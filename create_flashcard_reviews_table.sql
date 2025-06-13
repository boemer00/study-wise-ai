-- Create flashcard_reviews table for Supabase/PostgreSQL
-- This script avoids non-immutable functions in indexes to prevent 42P17 errors

-- First, let's add missing columns to existing flashcards table
ALTER TABLE flashcards
ADD COLUMN IF NOT EXISTS last_rating INTEGER;

ALTER TABLE flashcards
ADD COLUMN IF NOT EXISTS last_reviewed_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE flashcards
ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0;

-- Drop dependent objects first, then recreate the flashcard_reviews table
DROP VIEW IF EXISTS flashcard_review_stats CASCADE;
DROP TABLE IF EXISTS flashcard_reviews CASCADE;

CREATE TABLE flashcard_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flashcard_id UUID NOT NULL,
    user_id UUID NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 4),
    action TEXT DEFAULT 'review',
    review_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes without using functions that are not marked as immutable
-- Use simple column indexes instead of function-based indexes
CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_user_id ON flashcard_reviews (user_id);
CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_flashcard_id ON flashcard_reviews (flashcard_id);
CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_date ON flashcard_reviews (review_date);
CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_user_date ON flashcard_reviews (user_id, review_date);

-- Enable Row Level Security (RLS)
ALTER TABLE flashcard_reviews ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for flashcard_reviews
-- Policy for users to insert their own reviews
CREATE POLICY "Users can insert their own reviews"
ON flashcard_reviews FOR INSERT
WITH CHECK (true);  -- Allow all inserts for now - in production, use: auth.uid()::text = user_id

-- Policy for users to view their own reviews
CREATE POLICY "Users can view their own reviews"
ON flashcard_reviews FOR SELECT
USING (true);  -- Allow all reads for now - in production, use: auth.uid()::text = user_id

-- Policy for users to update their own reviews
CREATE POLICY "Users can update their own reviews"
ON flashcard_reviews FOR UPDATE
USING (true);  -- Allow all updates for now - in production, use: auth.uid()::text = user_id

-- Grant necessary permissions
GRANT ALL ON flashcard_reviews TO postgres;
GRANT ALL ON flashcard_reviews TO anon;
GRANT ALL ON flashcard_reviews TO authenticated;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;

-- Also ensure flashcards table has proper permissions
GRANT ALL ON flashcards TO postgres;
GRANT ALL ON flashcards TO anon;
GRANT ALL ON flashcards TO authenticated;

-- Create a view for easy review statistics
-- Note: Using existing flashcard table columns, not assuming next_review_date exists
CREATE OR REPLACE VIEW flashcard_review_stats AS
SELECT
    f.user_id,
    COUNT(DISTINCT f.id) as total_cards,
    COUNT(DISTINCT fr.id) as total_reviews,
    COUNT(DISTINCT CASE WHEN fr.review_date::date = CURRENT_DATE THEN fr.id END) as reviews_today,
    ROUND(AVG(fr.rating), 2) as avg_rating,
    -- Calculate cards due today as cards not reviewed today
    COUNT(DISTINCT f.id) - COUNT(DISTINCT CASE WHEN fr.review_date::date = CURRENT_DATE THEN fr.flashcard_id END) as cards_due_today
FROM flashcards f
LEFT JOIN flashcard_reviews fr ON f.id = fr.flashcard_id
GROUP BY f.user_id;

-- Grant permissions on the view
GRANT SELECT ON flashcard_review_stats TO postgres;
GRANT SELECT ON flashcard_review_stats TO anon;
GRANT SELECT ON flashcard_review_stats TO authenticated;

-- Refresh schema cache hint
NOTIFY pgrst, 'reload schema';
