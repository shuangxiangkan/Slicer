#!/usr/bin/env python3
"""
测试配置文件功能的脚本
验证修改配置文件后是否会影响程序行为
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import FileFinder


def test_config_modification():
    """测试配置文件修改功能"""
    print("🧪 测试配置文件修改功能")
    print("=" * 50)
    
    # 1. 读取原始配置
    config_path = Path(__file__).parent.parent / "parser" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        original_config = json.load(f)
    
    print("📖 原始配置:")
    print(f"   C扩展名: {original_config['file_extensions']['c_extensions']}")
    print(f"   跳过目录数量: {len(original_config['skip_directories'])}")
    
    # 2. 创建测试环境
    temp_dir = Path(tempfile.mkdtemp(prefix="config_test_"))
    print(f"\n📁 创建测试目录: {temp_dir}")
    
    # 创建测试文件
    test_files = [
        ("test.c", "int main() { return 0; }"),
        ("test.h", "int main();"),
        ("test.xyz", "// This is a .xyz file"),  # 新扩展名
        ("README.md", "# README"),  # 不支持的扩展名
    ]
    
    for filename, content in test_files:
        file_path = temp_dir / filename
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"   创建文件: {filename}")
    
    # 创建应该被跳过的目录
    skip_dir = temp_dir / "build"
    skip_dir.mkdir()
    with open(skip_dir / "temp.c", 'w') as f:
        f.write("int temp() { return 0; }")
    
    try:
        # 3. 测试原始配置
        print("\n🔍 使用原始配置测试:")
        finder1 = FileFinder()
        files1 = finder1.find_files(str(temp_dir))
        found_names1 = [Path(f).name for f in files1]
        print(f"   找到文件: {found_names1}")
        
        # 4. 修改配置文件
        print("\n⚙️  修改配置文件...")
        modified_config = original_config.copy()
        modified_config['file_extensions']['c_extensions'].append('.xyz')  # 添加新扩展名
        modified_config['skip_directories'].remove('build')  # 移除build目录跳过
        
        # 备份原配置并写入新配置
        backup_path = config_path.with_suffix('.json.backup')
        shutil.copy2(config_path, backup_path)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(modified_config, f, indent=2, ensure_ascii=False)
        
        print("   ✅ 配置文件已修改")
        print(f"   添加扩展名: .xyz")
        print(f"   移除跳过目录: build")
        
        # 5. 测试修改后的配置
        print("\n🔍 使用修改后配置测试:")
        finder2 = FileFinder()  # 重新创建实例以加载新配置
        files2 = finder2.find_files(str(temp_dir))
        found_names2 = [Path(f).name for f in files2]
        print(f"   找到文件: {found_names2}")
        
        # 6. 验证结果
        print("\n📊 验证结果:")
        if 'test.xyz' in found_names2 and 'test.xyz' not in found_names1:
            print("   ✅ 新扩展名 .xyz 配置生效")
        else:
            print("   ❌ 新扩展名 .xyz 配置未生效")
        
        if 'temp.c' in found_names2 and 'temp.c' not in found_names1:
            print("   ✅ build目录跳过配置修改生效")
        else:
            print("   ❌ build目录跳过配置修改未生效")
        
        # 7. 恢复原始配置
        print("\n🔄 恢复原始配置...")
        shutil.move(backup_path, config_path)
        print("   ✅ 配置文件已恢复")
        
        # 8. 验证恢复
        print("\n🔍 验证配置恢复:")
        finder3 = FileFinder()
        files3 = finder3.find_files(str(temp_dir))
        found_names3 = [Path(f).name for f in files3]
        print(f"   找到文件: {found_names3}")
        
        if found_names3 == found_names1:
            print("   ✅ 配置文件恢复成功")
        else:
            print("   ❌ 配置文件恢复失败")
        
    finally:
        # 清理测试环境
        shutil.rmtree(temp_dir)
        print(f"\n🧹 清理测试环境: {temp_dir}")
        
        # 确保配置文件恢复
        if backup_path.exists():
            shutil.move(backup_path, config_path)


def test_config_error_handling():
    """测试配置文件错误处理"""
    print("\n🧪 测试配置文件错误处理")
    print("=" * 50)
    
    config_path = Path(__file__).parent.parent / "parser" / "config.json"
    
    # 备份原配置
    backup_path = config_path.with_suffix('.json.backup2')
    shutil.copy2(config_path, backup_path)
    
    try:
        # 创建无效的配置文件
        print("📝 创建无效配置文件...")
        with open(config_path, 'w') as f:
            f.write("{ invalid json content }")
        
        # 测试错误处理
        print("🔍 测试错误处理...")
        try:
            finder = FileFinder()
            print("   ❌ 错误处理失败，应该抛出异常")
        except RuntimeError as e:
            print("   ✅ 错误处理正常，正确抛出了异常")
            print(f"   异常信息: {e}")
            
    finally:
        # 恢复配置
        shutil.move(backup_path, config_path)
        print("   🔄 配置文件已恢复")


def main():
    """主函数"""
    print("🚀 开始配置文件功能测试")
    print("=" * 60)
    
    try:
        test_config_modification()
        test_config_error_handling()
        print("\n🎉 所有配置文件测试完成！")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 