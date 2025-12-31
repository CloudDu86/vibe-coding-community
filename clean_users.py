"""清理 Supabase 中的所有用户数据"""
import asyncio
from supabase import create_client, Client
from src.config import settings

def main():
    """清理所有用户数据"""

    if settings.DEMO_MODE:
        print("❌ 当前处于演示模式，无法连接 Supabase")
        return

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("❌ 缺少 Supabase 配置信息")
        return

    # 创建 Supabase 客户端（使用 service_role_key 以绕过 RLS）
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )

    print("🧹 开始清理用户数据...\n")

    # 1. 删除消息
    try:
        result = supabase.table("messages").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ 已删除 messages 表数据")
    except Exception as e:
        print(f"⚠️  删除 messages 时出错: {e}")

    # 2. 删除回复
    try:
        result = supabase.table("responses").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ 已删除 responses 表数据")
    except Exception as e:
        print(f"⚠️  删除 responses 时出错: {e}")

    # 3. 删除帖子
    try:
        result = supabase.table("posts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ 已删除 posts 表数据")
    except Exception as e:
        print(f"⚠️  删除 posts 时出错: {e}")

    # 4. 删除解决者资料
    try:
        result = supabase.table("solver_profiles").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ 已删除 solver_profiles 表数据")
    except Exception as e:
        print(f"⚠️  删除 solver_profiles 时出错: {e}")

    # 5. 删除用户资料
    try:
        result = supabase.table("profiles").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"✅ 已删除 profiles 表数据")
    except Exception as e:
        print(f"⚠️  删除 profiles 时出错: {e}")

    # 6. 删除认证用户 (auth.users)
    # 注意：通过 Supabase Admin API 删除用户
    try:
        # 先获取所有用户
        response = supabase.auth.admin.list_users()
        users = response

        if hasattr(users, '__iter__'):
            user_list = list(users)
            print(f"\n📊 找到 {len(user_list)} 个认证用户")

            # 删除每个用户
            for user in user_list:
                try:
                    user_id = user.id if hasattr(user, 'id') else user.get('id')
                    supabase.auth.admin.delete_user(user_id)
                    print(f"   ✅ 已删除用户: {user_id}")
                except Exception as e:
                    print(f"   ❌ 删除用户 {user_id} 失败: {e}")
        else:
            print("⚠️  无法获取用户列表")

    except Exception as e:
        print(f"\n❌ 删除认证用户时出错: {e}")
        print("💡 提示：删除 auth.users 需要管理员权限，可能需要在 Supabase Dashboard 中手动删除")

    print("\n✨ 清理完成！所有用户数据已删除")

if __name__ == "__main__":
    main()
