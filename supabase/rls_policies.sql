-- ==============================================================================
-- SyllabusSync AI — Supabase Row Level Security (RLS) Policies
-- Project Ref: qdlnupgdtgmhvkknjmlv
-- ==============================================================================
-- SCHEMA & SECURITY FINDINGS:
--
-- 1. DIRECT BACKEND POSTGRESQL CONNECTION:
--    The SyllabusSync AI backend connects via the Supabase Transaction Pooler
--    (aws-0-ap-northeast-1.pooler.supabase.com:6543) using the 'postgres' role
--    (postgres.qdlnupgdtgmhvkknjmlv). In PostgreSQL, the 'postgres' role possesses
--    BYPASSRLS privileges. Direct backend SQL connections therefore bypass RLS.
--
--    Application-level tenant isolation in the FastAPI backend (via verified JWT identity,
--    ownership verification in auth.py, and SQL filtering on owner_user_id) remains MANDATORY
--    and serves as the primary defense boundary for all API routes.
--
-- 2. SCHEMA COLUMN TYPES (UUID vs TEXT):
--    Live schema inspection of the Supabase PostgreSQL database confirms:
--    - courses.owner_user_id: UUID
--    - syllabi.owner_user_id: UUID
--    - study_plans.owner_user_id: UUID
--    - user_settings.owner_user_id: UUID
--    - user_settings.id: TEXT
--
--    Since Supabase auth.uid() returns type UUID, direct comparison:
--    owner_user_id = auth.uid()
--    is type-safe for all UUID columns.
--    For user_settings.id (TEXT), casting (auth.uid())::text is used.
--
-- 3. CLIENT-FACING / POSTGREST ACCESS:
--    These RLS policies secure direct client requests (e.g., Supabase JS client with anon
--    or authenticated JWT tokens). They guarantee that even if an attacker interacts directly
--    with the Supabase PostgREST endpoints, they can only view, modify, or delete their own
--    records.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Enable RLS on all 13 tables
-- ------------------------------------------------------------------------------
ALTER TABLE IF EXISTS syllabi ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS course_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS study_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS study_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS video_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS topic_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS rejected_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS youtube_search_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS syllabus_coverage_summary ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 2. Direct Ownership Policies: syllabi
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "syllabi_owner_select" ON syllabi;
CREATE POLICY "syllabi_owner_select" ON syllabi
    FOR SELECT
    USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "syllabi_owner_insert" ON syllabi;
CREATE POLICY "syllabi_owner_insert" ON syllabi
    FOR INSERT
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "syllabi_owner_update" ON syllabi;
CREATE POLICY "syllabi_owner_update" ON syllabi
    FOR UPDATE
    USING (owner_user_id = auth.uid())
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "syllabi_owner_delete" ON syllabi;
CREATE POLICY "syllabi_owner_delete" ON syllabi
    FOR DELETE
    USING (owner_user_id = auth.uid());

-- ------------------------------------------------------------------------------
-- 3. Direct Ownership Policies: courses
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "courses_owner_select" ON courses;
CREATE POLICY "courses_owner_select" ON courses
    FOR SELECT
    USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "courses_owner_insert" ON courses;
CREATE POLICY "courses_owner_insert" ON courses
    FOR INSERT
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "courses_owner_update" ON courses;
CREATE POLICY "courses_owner_update" ON courses
    FOR UPDATE
    USING (owner_user_id = auth.uid())
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "courses_owner_delete" ON courses;
CREATE POLICY "courses_owner_delete" ON courses
    FOR DELETE
    USING (owner_user_id = auth.uid());

-- ------------------------------------------------------------------------------
-- 4. Direct Ownership Policies: study_plans
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "study_plans_owner_select" ON study_plans;
CREATE POLICY "study_plans_owner_select" ON study_plans
    FOR SELECT
    USING (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "study_plans_owner_insert" ON study_plans;
CREATE POLICY "study_plans_owner_insert" ON study_plans
    FOR INSERT
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "study_plans_owner_update" ON study_plans;
CREATE POLICY "study_plans_owner_update" ON study_plans
    FOR UPDATE
    USING (owner_user_id = auth.uid())
    WITH CHECK (owner_user_id = auth.uid());

DROP POLICY IF EXISTS "study_plans_owner_delete" ON study_plans;
CREATE POLICY "study_plans_owner_delete" ON study_plans
    FOR DELETE
    USING (owner_user_id = auth.uid());

-- ------------------------------------------------------------------------------
-- 5. Direct Ownership Policies: user_settings
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "user_settings_owner_select" ON user_settings;
CREATE POLICY "user_settings_owner_select" ON user_settings
    FOR SELECT
    USING (owner_user_id = auth.uid() OR id = (auth.uid())::text);

DROP POLICY IF EXISTS "user_settings_owner_insert" ON user_settings;
CREATE POLICY "user_settings_owner_insert" ON user_settings
    FOR INSERT
    WITH CHECK (owner_user_id = auth.uid() OR id = (auth.uid())::text);

DROP POLICY IF EXISTS "user_settings_owner_update" ON user_settings;
CREATE POLICY "user_settings_owner_update" ON user_settings
    FOR UPDATE
    USING (owner_user_id = auth.uid() OR id = (auth.uid())::text)
    WITH CHECK (owner_user_id = auth.uid() OR id = (auth.uid())::text);

DROP POLICY IF EXISTS "user_settings_owner_delete" ON user_settings;
CREATE POLICY "user_settings_owner_delete" ON user_settings
    FOR DELETE
    USING (owner_user_id = auth.uid() OR id = (auth.uid())::text);

-- ------------------------------------------------------------------------------
-- 6. Relational Ownership Policies: course_assessments (via courses)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "course_assessments_rel_select" ON course_assessments;
CREATE POLICY "course_assessments_rel_select" ON course_assessments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM courses c
            WHERE c.id = course_assessments.course_id
              AND c.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "course_assessments_rel_insert" ON course_assessments;
CREATE POLICY "course_assessments_rel_insert" ON course_assessments
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM courses c
            WHERE c.id = course_assessments.course_id
              AND c.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "course_assessments_rel_update" ON course_assessments;
CREATE POLICY "course_assessments_rel_update" ON course_assessments
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM courses c
            WHERE c.id = course_assessments.course_id
              AND c.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM courses c
            WHERE c.id = course_assessments.course_id
              AND c.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "course_assessments_rel_delete" ON course_assessments;
CREATE POLICY "course_assessments_rel_delete" ON course_assessments
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM courses c
            WHERE c.id = course_assessments.course_id
              AND c.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 7. Relational Ownership Policies: modules (via syllabi)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "modules_rel_select" ON modules;
CREATE POLICY "modules_rel_select" ON modules
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = modules.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "modules_rel_insert" ON modules;
CREATE POLICY "modules_rel_insert" ON modules
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = modules.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "modules_rel_update" ON modules;
CREATE POLICY "modules_rel_update" ON modules
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = modules.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = modules.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "modules_rel_delete" ON modules;
CREATE POLICY "modules_rel_delete" ON modules
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = modules.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 8. Relational Ownership Policies: topics (via syllabi)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "topics_rel_select" ON topics;
CREATE POLICY "topics_rel_select" ON topics
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topics.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topics_rel_insert" ON topics;
CREATE POLICY "topics_rel_insert" ON topics
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topics.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topics_rel_update" ON topics;
CREATE POLICY "topics_rel_update" ON topics
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topics.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topics.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topics_rel_delete" ON topics;
CREATE POLICY "topics_rel_delete" ON topics
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topics.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 9. Relational Ownership Policies: study_tasks (via study_plans)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "study_tasks_rel_select" ON study_tasks;
CREATE POLICY "study_tasks_rel_select" ON study_tasks
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM study_plans sp
            WHERE sp.id = study_tasks.plan_id
              AND sp.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "study_tasks_rel_insert" ON study_tasks;
CREATE POLICY "study_tasks_rel_insert" ON study_tasks
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM study_plans sp
            WHERE sp.id = study_tasks.plan_id
              AND sp.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "study_tasks_rel_update" ON study_tasks;
CREATE POLICY "study_tasks_rel_update" ON study_tasks
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM study_plans sp
            WHERE sp.id = study_tasks.plan_id
              AND sp.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM study_plans sp
            WHERE sp.id = study_tasks.plan_id
              AND sp.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "study_tasks_rel_delete" ON study_tasks;
CREATE POLICY "study_tasks_rel_delete" ON study_tasks
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM study_plans sp
            WHERE sp.id = study_tasks.plan_id
              AND sp.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 10. Relational Ownership Policies: topic_resources (via syllabi)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "topic_resources_rel_select" ON topic_resources;
CREATE POLICY "topic_resources_rel_select" ON topic_resources
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topic_resources.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topic_resources_rel_insert" ON topic_resources;
CREATE POLICY "topic_resources_rel_insert" ON topic_resources
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topic_resources.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topic_resources_rel_update" ON topic_resources;
CREATE POLICY "topic_resources_rel_update" ON topic_resources
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topic_resources.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topic_resources.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "topic_resources_rel_delete" ON topic_resources;
CREATE POLICY "topic_resources_rel_delete" ON topic_resources
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = topic_resources.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 11. Relational Ownership Policies: rejected_channels (via syllabi)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "rejected_channels_rel_select" ON rejected_channels;
CREATE POLICY "rejected_channels_rel_select" ON rejected_channels
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = rejected_channels.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "rejected_channels_rel_insert" ON rejected_channels;
CREATE POLICY "rejected_channels_rel_insert" ON rejected_channels
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = rejected_channels.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "rejected_channels_rel_update" ON rejected_channels;
CREATE POLICY "rejected_channels_rel_update" ON rejected_channels
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = rejected_channels.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = rejected_channels.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "rejected_channels_rel_delete" ON rejected_channels;
CREATE POLICY "rejected_channels_rel_delete" ON rejected_channels
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = rejected_channels.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 12. Relational Ownership Policies: syllabus_coverage_summary (via syllabi)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "coverage_summary_rel_select" ON syllabus_coverage_summary;
CREATE POLICY "coverage_summary_rel_select" ON syllabus_coverage_summary
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = syllabus_coverage_summary.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "coverage_summary_rel_insert" ON syllabus_coverage_summary;
CREATE POLICY "coverage_summary_rel_insert" ON syllabus_coverage_summary
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = syllabus_coverage_summary.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "coverage_summary_rel_update" ON syllabus_coverage_summary;
CREATE POLICY "coverage_summary_rel_update" ON syllabus_coverage_summary
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = syllabus_coverage_summary.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = syllabus_coverage_summary.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "coverage_summary_rel_delete" ON syllabus_coverage_summary;
CREATE POLICY "coverage_summary_rel_delete" ON syllabus_coverage_summary
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM syllabi s
            WHERE s.id = syllabus_coverage_summary.syllabus_id
              AND s.owner_user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 13. Shared Tables: video_resources & youtube_search_cache
-- ------------------------------------------------------------------------------
-- Hardened: Only authenticated SELECT is permitted via client-facing PostgREST.
-- Direct client INSERT, UPDATE, and DELETE are strictly denied.
-- All cache writes, updates, and maintenance are handled exclusively server-side
-- by the FastAPI backend connecting via the 'postgres' role (BYPASSRLS).

-- 13a. video_resources
DROP POLICY IF EXISTS "video_resources_auth_select" ON video_resources;
DROP POLICY IF EXISTS "video_resources_auth_insert" ON video_resources;
DROP POLICY IF EXISTS "video_resources_auth_update" ON video_resources;
DROP POLICY IF EXISTS "video_resources_auth_delete" ON video_resources;

CREATE POLICY "video_resources_auth_select" ON video_resources
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- 13b. youtube_search_cache
DROP POLICY IF EXISTS "youtube_search_cache_auth_select" ON youtube_search_cache;
DROP POLICY IF EXISTS "youtube_search_cache_auth_insert" ON youtube_search_cache;
DROP POLICY IF EXISTS "youtube_search_cache_auth_update" ON youtube_search_cache;
DROP POLICY IF EXISTS "youtube_search_cache_auth_delete" ON youtube_search_cache;

CREATE POLICY "youtube_search_cache_auth_select" ON youtube_search_cache
    FOR SELECT
    USING (auth.role() = 'authenticated');
