-- StudyWise AI - Safe Documents Table Migration
-- This script adds only the missing columns to your existing documents table without disrupting anything.

-- ========================================================================
-- STEP 1: Add the essential missing columns
-- ========================================================================

-- Add user_id column (required for the errors you're seeing)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Add application column (required for PDF metadata)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS application VARCHAR(255);

-- ========================================================================
-- STEP 2: Add enhanced PDF/DOCX metadata fields (optional but useful)
-- ========================================================================

-- Document authoring info
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS author VARCHAR(255);

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS creation_date TIMESTAMPTZ;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS modification_date TIMESTAMPTZ;

-- Document content metrics
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS word_count INTEGER;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS page_count INTEGER;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS paragraph_count INTEGER;

-- Document properties
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS language VARCHAR(50);

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS pdf_version VARCHAR(20);

-- Content features
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS has_tables BOOLEAN DEFAULT FALSE;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS has_images BOOLEAN DEFAULT FALSE;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(100);

-- ========================================================================
-- STEP 3: Add flashcards_count (to match our API expectations)
-- ========================================================================

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS flashcards_count INTEGER DEFAULT 0;

-- ========================================================================
-- STEP 4: Add indexes for performance (safe to add)
-- ========================================================================

-- Index for user queries (most important)
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- Index for file type filtering
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- ========================================================================
-- STEP 5: Update existing documents with default user_id (optional)
-- ========================================================================

-- Set a default user_id for existing documents (if any exist)
-- You can change 'demo-user-123' to your preferred default
UPDATE documents
SET user_id = 'demo-user-123'
WHERE user_id IS NULL;

-- ========================================================================
-- STEP 6: Verification queries
-- ========================================================================

-- Check that all columns were added successfully
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'documents'
ORDER BY ordinal_position;

-- Count existing documents
SELECT
    COUNT(*) as total_documents,
    COUNT(user_id) as documents_with_user_id,
    COUNT(CASE WHEN weaviate_synced = true THEN 1 END) as synced_to_weaviate
FROM documents;

-- Show sample of updated structure
SELECT
    document_id,
    title,
    user_id,
    file_type,
    status,
    weaviate_synced
FROM documents
LIMIT 3;
