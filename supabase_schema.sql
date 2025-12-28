-- AI创造互助社区 - Supabase 数据库 Schema
-- 在 Supabase SQL Editor 中执行此脚本

-- =====================================================
-- 1. 用户资料表 (profiles)
-- =====================================================
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nickname VARCHAR(50) NOT NULL,
    avatar_url TEXT,
    user_role VARCHAR(20) NOT NULL CHECK (user_role IN ('asker', 'solver', 'both')),
    real_name VARCHAR(50),
    id_card_verified BOOLEAN DEFAULT FALSE,
    phone VARCHAR(20),
    wechat_id VARCHAR(50),
    bio TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 2. 解决者资料表 (solver_profiles)
-- =====================================================
CREATE TABLE public.solver_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    experience_years INTEGER,
    expertise_areas TEXT[],
    resume TEXT,
    portfolio_urls TEXT[],
    hourly_rate DECIMAL(10,2),
    rating DECIMAL(3,2) DEFAULT 0.00,
    total_solved INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- =====================================================
-- 3. 分类表 (categories)
-- =====================================================
CREATE TABLE public.categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 初始分类数据
INSERT INTO public.categories (name, slug, description, display_order) VALUES
    ('网页开发', 'web', '网站、Web应用相关问题', 1),
    ('移动App', 'app', 'iOS/Android应用开发问题', 2),
    ('微信小程序', 'wechat-mini', '微信小程序开发问题', 3),
    ('桌面应用', 'desktop', '桌面软件开发问题', 4),
    ('后端服务', 'backend', 'API、数据库、服务器问题', 5),
    ('AI/机器学习', 'ai-ml', 'AI模型、机器学习相关问题', 6),
    ('Web3开发', 'web3', '区块链、智能合约、DApp开发问题', 7),
    ('音视频开发', 'av', '音频、视频处理与流媒体开发问题', 8),
    ('其他', 'other', '其他类型问题', 99);

-- =====================================================
-- 4. 求助帖子表 (posts)
-- =====================================================
CREATE TABLE public.posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES public.categories(id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    ai_tool_used VARCHAR(100),
    error_message TEXT,
    code_snippet TEXT,
    screenshot_urls TEXT[],
    budget_type VARCHAR(20) CHECK (budget_type IN ('fixed', 'hourly', 'negotiable')),
    budget_amount DECIMAL(10,2),
    urgency VARCHAR(20) DEFAULT 'medium' CHECK (urgency IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    view_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 5. 解决方案回复表 (responses)
-- =====================================================
CREATE TABLE public.responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    solver_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    proposed_solution TEXT,
    estimated_time VARCHAR(50),
    proposed_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'completed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, solver_id)
);

-- =====================================================
-- 索引
-- =====================================================
CREATE INDEX idx_posts_category ON public.posts(category_id);
CREATE INDEX idx_posts_author ON public.posts(author_id);
CREATE INDEX idx_posts_status ON public.posts(status);
CREATE INDEX idx_posts_created_at ON public.posts(created_at DESC);
CREATE INDEX idx_responses_post ON public.responses(post_id);
CREATE INDEX idx_responses_solver ON public.responses(solver_id);
CREATE INDEX idx_solver_profiles_user ON public.solver_profiles(user_id);

-- =====================================================
-- 启用 Row Level Security (RLS)
-- =====================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.solver_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS 策略 - profiles
-- =====================================================
CREATE POLICY "Profiles are viewable by everyone"
    ON public.profiles FOR SELECT USING (true);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- =====================================================
-- RLS 策略 - solver_profiles
-- =====================================================
CREATE POLICY "Solver profiles are viewable by everyone"
    ON public.solver_profiles FOR SELECT USING (true);

CREATE POLICY "Solvers can update own profile"
    ON public.solver_profiles FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Solvers can insert own profile"
    ON public.solver_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);

-- =====================================================
-- RLS 策略 - categories
-- =====================================================
CREATE POLICY "Categories are viewable by everyone"
    ON public.categories FOR SELECT USING (true);

-- =====================================================
-- RLS 策略 - posts
-- =====================================================
CREATE POLICY "Posts are viewable by everyone"
    ON public.posts FOR SELECT USING (true);

CREATE POLICY "Authenticated users can create posts"
    ON public.posts FOR INSERT WITH CHECK (auth.uid() = author_id);

CREATE POLICY "Authors can update own posts"
    ON public.posts FOR UPDATE USING (auth.uid() = author_id);

CREATE POLICY "Authors can delete own posts"
    ON public.posts FOR DELETE USING (auth.uid() = author_id);

-- =====================================================
-- RLS 策略 - responses
-- =====================================================
CREATE POLICY "Responses are viewable by everyone"
    ON public.responses FOR SELECT USING (true);

CREATE POLICY "Solvers can create responses"
    ON public.responses FOR INSERT WITH CHECK (auth.uid() = solver_id);

CREATE POLICY "Solvers can update own responses"
    ON public.responses FOR UPDATE USING (auth.uid() = solver_id);

-- =====================================================
-- 更新时间触发器
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_solver_profiles_updated_at
    BEFORE UPDATE ON public.solver_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON public.posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_responses_updated_at
    BEFORE UPDATE ON public.responses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 6. 消息通知表 (messages)
-- =====================================================
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('system', 'order', 'user')),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    related_post_id UUID REFERENCES public.posts(id) ON DELETE SET NULL,
    related_response_id UUID REFERENCES public.responses(id) ON DELETE SET NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 消息索引
CREATE INDEX idx_messages_recipient ON public.messages(recipient_id);
CREATE INDEX idx_messages_is_read ON public.messages(recipient_id, is_read);
CREATE INDEX idx_messages_created_at ON public.messages(created_at DESC);

-- 启用 RLS
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- RLS 策略 - messages
CREATE POLICY "Users can view own messages"
    ON public.messages FOR SELECT USING (auth.uid() = recipient_id);

CREATE POLICY "Users can update own messages"
    ON public.messages FOR UPDATE USING (auth.uid() = recipient_id);

CREATE POLICY "System can insert messages"
    ON public.messages FOR INSERT WITH CHECK (true);
