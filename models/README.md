# 公众号采集助手数据库模块

## 概述

本模块实现了公众号采集助手的数据库功能，包括用户账号管理和公众号文章数据存储。数据库使用Supabase云服务，提供安全、高效的数据存储和访问能力。

## 数据库设置

### 1. Supabase设置

1. 注册并登录[Supabase](https://supabase.com/)
2. 创建新项目
3. 在SQL编辑器中执行`models/supabase_schema.sql`脚本创建所需的数据表
4. 在项目设置中获取API URL和API Key
5. 将API URL和API Key填入项目根目录的`.env`文件中

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 2. 安装依赖

```bash
pip install supabase python-dotenv
```

## 数据库结构

### 用户表 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，用户ID |
| email | TEXT | 用户邮箱，唯一 |
| nickname | TEXT | 用户昵称 |
| mac_address | TEXT | 绑定的MAC地址 |
| activation_code | TEXT | 激活码 |
| expiry_date | TIMESTAMP | 授权过期日期 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 激活码表 (activation_codes)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| code | TEXT | 激活码，唯一 |
| duration_days | INTEGER | 有效期天数 |
| used | BOOLEAN | 是否已使用 |
| used_by | UUID | 使用者ID |
| used_at | TIMESTAMP | 使用时间 |
| created_at | TIMESTAMP | 创建时间 |
| created_by | TEXT | 创建者 |

### 文章表 (articles)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户ID，外键 |
| account_name | TEXT | 公众号名称 |
| category | TEXT | 公众号分类 |
| title | TEXT | 文章标题 |
| content | TEXT | 文章内