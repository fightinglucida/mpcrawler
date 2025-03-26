-- 用户表
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    nickname TEXT NOT NULL,
    mac_address TEXT,
    activation_code TEXT,
    expiry_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 激活码表
CREATE TABLE IF NOT EXISTS public.activation_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE,
    duration_days INTEGER NOT NULL DEFAULT 30,
    used BOOLEAN DEFAULT FALSE,
    used_by UUID REFERENCES public.users(id),
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT
);

-- 文章表
CREATE TABLE IF NOT EXISTS public.articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    account_name TEXT NOT NULL,
    category TEXT DEFAULT '未分类',
    title TEXT NOT NULL,
    content TEXT,
    publish_time TIMESTAMP WITH TIME ZONE,
    read_count INTEGER DEFAULT 0,
    article_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_articles_user_id ON public.articles(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_account_name ON public.articles(account_name);
CREATE INDEX IF NOT EXISTS idx_articles_publish_time ON public.articles(publish_time);

-- 启用行级安全策略
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activation_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;

-- 用户表的安全策略
CREATE POLICY "允许未认证用户注册" ON public.users
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "允许查看用户信息" ON public.users
    FOR SELECT
    USING (true);

CREATE POLICY "用户只能更新自己的信息" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "允许服务端操作" ON public.users
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 文章表的安全策略
CREATE POLICY "用户只能查看自己的文章" ON public.articles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "用户只能插入自己的文章" ON public.articles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "用户只能更新自己的文章" ON public.articles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "用户只能删除自己的文章" ON public.articles
    FOR DELETE USING (auth.uid() = user_id);

-- 激活码表的安全策略
CREATE POLICY "只有管理员可以创建激活码" ON public.activation_codes
    FOR INSERT WITH CHECK (auth.uid() IN (
        SELECT id FROM public.users WHERE email = 'admin@example.com'
    ));

CREATE POLICY "用户可以查看未使用的激活码" ON public.activation_codes
    FOR SELECT USING (NOT used OR used_by = auth.uid());