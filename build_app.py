import os
import sys
import shutil
from pathlib import Path

# 创建打包脚本
def build_app():
    print("开始打包应用...")
    
    # 确保环境变量文件存在
    env_file = Path('.env')
    if not env_file.exists():
        print("警告: .env 文件不存在，将创建一个空的环境变量文件")
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("# 环境变量配置\n")
            f.write("SUPABASE_URL=your_supabase_url\n")
            f.write("SUPABASE_KEY=your_supabase_key\n")
    
    # 创建assets目录（如果不存在）
    assets_dir = Path('assets')
    if not assets_dir.exists():
        os.makedirs(assets_dir)
        print("创建assets目录")
    
    # 确保图标文件存在
    icon_file = assets_dir / 'icon.ico'
    if not icon_file.exists():
        # 如果没有ico文件，尝试使用svg文件转换
        svg_file = assets_dir / 'icon.svg'
        if svg_file.exists():
            try:
                from PIL import Image
                import cairosvg
                
                # 转换SVG到PNG
                png_file = assets_dir / 'icon.png'
                cairosvg.svg2png(url=str(svg_file), write_to=str(png_file), output_width=256, output_height=256)
                
                # 转换PNG到ICO
                img = Image.open(png_file)
                img.save(icon_file)
                print(f"已将SVG图标转换为ICO格式: {icon_file}")
            except Exception as e:
                print(f"转换图标失败: {str(e)}")
                print("请手动提供一个icon.ico文件在assets目录下")
        else:
            print("警告: 未找到图标文件，请在assets目录中提供icon.ico或icon.svg文件")
    
    # 构建PyInstaller命令
    icon_path = str(icon_file) if icon_file.exists() else ""
    icon_option = f"--icon={icon_path}" if icon_path else ""
    
    # 使用PyInstaller打包
    pyinstaller_cmd = (
        f"pyinstaller --noconfirm --onefile --windowed "
        f"{icon_option} "
        "--add-data \"config.json;.\" "
        "--add-data \"assets;assets\" "
        "--collect-data \"fake_useragent\" "
        "--hidden-import=PyQt6 "
        "--hidden-import=pandas "
        "--hidden-import=openpyxl "
        "--hidden-import=beautifulsoup4 "
        "--hidden-import=supabase "
        "--hidden-import=bcrypt "
        "--hidden-import=PIL "
        "--hidden-import=fake_useragent "
        "--hidden-import=python-dotenv "
        "--hidden-import=requests "
        "--hidden-import=lxml "
        "--hidden-import=queue "
        "--hidden-import=python-dateutil "
        "--hidden-import=cryptography "
        "user_app.py"
    )
    
    # 执行打包命令
    print("执行PyInstaller打包命令...")
    os.system(pyinstaller_cmd)
    
    print("打包完成！")
    print(f"可执行文件位于: {os.path.abspath('dist/user_app.exe')}")

if __name__ == "__main__":
    build_app()
