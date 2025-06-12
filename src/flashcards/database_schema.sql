-- FSRS Database Schema Migration
-- This script creates the necessary tables and indices for FSRS implementation

-- Create FSRS card states table
CREATE TABLE IF NOT EXISTS fsrs_card_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    -- FSRS core parameters
    stability REAL NOT NULL DEFAULT 0.4,  -- Memory stability in days
    difficulty REAL NOT NULL DEFAULT 5.0, -- Card difficulty (1-10)
    due_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Review tracking
    last_reviewed TIMESTAMP WITH TIME ZONE,
    total_reviews INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0, -- Number of times forgotten

    -- State information
    state TEXT NOT NULL DEFAULT 'new', -- new, learning, review, relearning
    reps INTEGER DEFAULT 0, -- Successful review count

    -- Performance tracking
    elapsed_days INTEGER, -- Days since last review
    scheduled_days INTEGER, -- Originally scheduled interval

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(flashcard_id, user_id),
    CHECK (stability >= 0.1 AND stability <= 36500),
    CHECK (difficulty >= 1.0 AND difficulty <= 10.0),
    CHECK (total_reviews >= 0),
    CHECK (lapses >= 0),
    CHECK (reps >= 0)
);

-- Create FSRS parameters table (for personalized parameters)
CREATE TABLE IF NOT EXISTS fsrs_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID, -- NULL for default parameters

    -- FSRS weight parameters (17 values)
    w JSONB NOT NULL DEFAULT '[0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234, 1.616, 0.1544, 0.9849, 2.18, 0.11, 5.0, 2.4, 1.0, 2.0, 1.0]',

    -- Scheduling constraints
    maximum_interval INTEGER DEFAULT 36500,
    request_retention REAL DEFAULT 0.9,

    -- Metadata
    version TEXT DEFAULT '4.5',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    optimized_for_user BOOLEAN DEFAULT FALSE,

    -- Constraints
    CHECK (maximum_interval >= 1 AND maximum_interval <= 36500),
    CHECK (request_retention >= 0.7 AND request_retention <= 0.97),
    UNIQUE(user_id) -- One parameter set per user
);

-- Create review history table for analytics and optimization
CREATE TABLE IF NOT EXISTS fsrs_review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,

    -- Review data
    rating INTEGER NOT NULL, -- 1=AGAIN, 2=HARD, 3=GOOD, 4=EASY
    review_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    elapsed_days INTEGER NOT NULL,

    -- FSRS state before review
    stability_before REAL NOT NULL,
    difficulty_before REAL NOT NULL,
    retrievability REAL NOT NULL,

    -- FSRS state after review
    stability_after REAL NOT NULL,
    difficulty_after REAL NOT NULL,
    interval_days INTEGER NOT NULL,

    -- Performance metrics
    response_time_ms INTEGER, -- Response time in milliseconds
    session_id UUID, -- Study session identifier

    -- Constraints
    CHECK (rating >= 1 AND rating <= 4),
    CHECK (elapsed_days >= 0),
    CHECK (stability_before >= 0.1),
    CHECK (difficulty_before >= 1.0 AND difficulty_before <= 10.0),
    CHECK (retrievability >= 0.0 AND retrievability <= 1.0),
    CHECK (stability_after >= 0.1),
    CHECK (difficulty_after >= 1.0 AND difficulty_after <= 10.0),
    CHECK (interval_days >= 0)
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_fsrs_states_due ON fsrs_card_states (user_id, due_date);
CREATE INDEX IF NOT EXISTS idx_fsrs_states_flashcard ON fsrs_card_states (flashcard_id);
CREATE INDEX IF NOT EXISTS idx_fsrs_states_updated ON fsrs_card_states (updated_at);
CREATE INDEX IF NOT EXISTS idx_fsrs_parameters_user ON fsrs_parameters (user_id);
CREATE INDEX IF NOT EXISTS idx_fsrs_history_user ON fsrs_review_history (user_id, review_time);
CREATE INDEX IF NOT EXISTS idx_fsrs_history_flashcard ON fsrs_review_history (flashcard_id);
CREATE INDEX IF NOT EXISTS idx_fsrs_history_session ON fsrs_review_history (session_id);

-- Insert default FSRS parameters
INSERT INTO fsrs_parameters (user_id, optimized_for_user)
VALUES (NULL, FALSE)
ON CONFLICT (user_id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for automatic updated_at
CREATE TRIGGER update_fsrs_card_states_updated_at
    BEFORE UPDATE ON fsrs_card_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for due cards with flashcard information
CREATE OR REPLACE VIEW fsrs_due_cards AS
SELECT
    f.id as flashcard_id,
    f.question,
    f.answer,
    f.tags,
    f.level,
    fcs.user_id,
    fcs.stability,
    fcs.difficulty,
    fcs.due_date,
    fcs.last_reviewed,
    fcs.total_reviews,
    fcs.state,
    fcs.reps,
    CASE
        WHEN fcs.due_date <= NOW() THEN TRUE
        ELSE FALSE
    END as is_due,
    EXTRACT(DAYS FROM NOW() - fcs.due_date)::INTEGER as days_overdue
FROM flashcards f
JOIN fsrs_card_states fcs ON f.id = fcs.flashcard_id
WHERE fcs.due_date <= NOW()
ORDER BY fcs.due_date ASC, fcs.difficulty DESC;

-- Create view for scheduling metrics
CREATE OR REPLACE VIEW fsrs_user_metrics AS
SELECT
    fcs.user_id,
    COUNT(*) as total_cards,
    COUNT(*) FILTER (WHERE fcs.due_date <= NOW()) as cards_due_today,
    COUNT(*) FILTER (WHERE fcs.due_date < NOW() - INTERVAL '1 day') as overdue_cards,
    AVG(fcs.stability) as avg_stability,
    AVG(fcs.difficulty) as avg_difficulty,
    COUNT(*) FILTER (WHERE fcs.state = 'new') as new_cards,
    COUNT(*) FILTER (WHERE fcs.state = 'learning') as learning_cards,
    COUNT(*) FILTER (WHERE fcs.state = 'review') as review_cards,
    MAX(fcs.updated_at) as last_activity
FROM fsrs_card_states fcs
GROUP BY fcs.user_id;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON fsrs_card_states TO authenticated;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON fsrs_parameters TO authenticated;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON fsrs_review_history TO authenticated;
-- GRANT SELECT ON fsrs_due_cards TO authenticated;
-- GRANT SELECT ON fsrs_user_metrics TO authenticated;
