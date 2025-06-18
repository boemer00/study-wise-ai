-- Disable ALL RLS for MVP
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE flashcards DISABLE ROW LEVEL SECURITY;
ALTER TABLE flashcard_reviews DISABLE ROW LEVEL SECURITY;

-- Drop all policies
DROP POLICY IF EXISTS "Users can insert their own reviews" ON flashcard_reviews;
DROP POLICY IF EXISTS "Users can view their own reviews" ON flashcard_reviews;
DROP POLICY IF EXISTS "Users can update their own reviews" ON flashcard_reviews;
DROP POLICY IF EXISTS "Users can delete their own reviews" ON flashcard_reviews;

DROP POLICY IF EXISTS "Users can insert their own flashcards" ON flashcards;
DROP POLICY IF EXISTS "Users can view their own flashcards" ON flashcards;
DROP POLICY IF EXISTS "Users can update their own flashcards" ON flashcards;
DROP POLICY IF EXISTS "Users can delete their own flashcards" ON flashcards;

DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

-- Verify
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

SELECT 'MVP READY - NO AUTHENTICATION' as status;