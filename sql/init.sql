-- 创建猫咪档案表
CREATE TABLE cats (
    cat_id SERIAL PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,            -- 昵称 
    gender VARCHAR(10),                       -- 性别 
    color VARCHAR(30),                        -- 毛色 
    personality_tags TEXT[],                  -- 性格标签 
    health_status VARCHAR(50) DEFAULT '健康', -- 健康状态 
    is_neutered BOOLEAN DEFAULT FALSE,        -- 绝育状态 
    last_seen_location GEOMETRY(Point, 4326), -- 最后出现位置 (GIS) [cite: 26]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建用户表
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    role VARCHAR(20) DEFAULT 'user',          -- 角色: admin/user [cite: 23]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建打卡/记录表
CREATE TABLE check_ins (
    record_id SERIAL PRIMARY KEY,
    cat_id INT REFERENCES cats(cat_id) ON DELETE CASCADE,
    user_id INT REFERENCES users(user_id),
    type VARCHAR(20),                         -- 'encounter' (偶遇) 或 'feeding' (投喂) [cite: 26, 27]
    location GEOMETRY(Point, 4326) NOT NULL,  -- GPS 坐标 [cite: 26]
    photo_url VARCHAR(255),
    comment TEXT,                             -- 用户评论 [cite: 26]
    status VARCHAR(20) DEFAULT 'pending',     -- 审核状态: pending/approved [cite: 23, 26]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引设计
CREATE INDEX idx_cats_health ON cats(health_status);
CREATE INDEX idx_checkins_cat_id ON check_ins(cat_id);