import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import configparser

def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.ini中读取target_scan_path，若失败则返回default_root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    if os.path.isfile(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            path = config.get('CORE', 'target_scan_path', fallback=None)
            if path:
                path = path.strip()
                # 相对路径转换为相对于脚本目录的绝对路径
                if not os.path.isabs(path):
                    path = os.path.join(script_dir, path)
                return path
        except Exception:
            pass
    return default_root if default_root is not None else os.getcwd()

# 定义等级映射
GRADE_MAPPING = {
    '1': 'ZAYIN',
    '2': 'TETH', 
    '3': 'HE',
    '4': 'WAW',
    '5': 'ALEPH'
}

def should_process_file(file_path):
    """判断是否应该处理该文件"""
    filename = os.path.basename(file_path)
    
    # 跳过 BaseEquipment.txt 文件
    if filename.lower() == "baseequipment.txt":
        return False
    
    # 只处理 .txt 和 .xml 文件
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ('.txt', '.xml')

def map_grade(grade_value):
    """将数字等级映射为对应的名称"""
    # 先移除可能的空格
    grade_value = grade_value.strip() if grade_value else grade_value
    return GRADE_MAPPING.get(grade_value, grade_value)

def resolve_symlink(path):
    """解析符号链接，返回真实路径"""
    try:
        return os.path.realpath(path)
    except:
        return path

def get_mod_folder_and_time(file_path, root_path):
    """获取文件所属的模组文件夹和修改时间"""
    try:
        # 解析符号链接
        real_file_path = resolve_symlink(file_path)
        real_root_path = resolve_symlink(root_path)
        
        # 获取文件相对于根路径的相对路径
        try:
            rel_path = os.path.relpath(real_file_path, real_root_path)
        except ValueError:
            # 如果不在同一驱动器，尝试直接使用绝对路径
            rel_path = real_file_path
        
        # 分割相对路径，第一个部分应该是模组文件夹名
        path_parts = rel_path.split(os.sep)
        
        if len(path_parts) > 1 and path_parts[0] != '..' and path_parts[0] != '.':
            mod_folder_name = path_parts[0]
            mod_folder_path = os.path.join(real_root_path, mod_folder_name)
            
            # 获取模组文件夹的修改时间
            if os.path.exists(mod_folder_path):
                mod_time = os.path.getmtime(mod_folder_path)
                return mod_folder_name, mod_time, mod_folder_path
            else:
                return mod_folder_name, None, None
        else:
            # 如果文件直接在根路径下，没有模组文件夹
            return "Root", os.path.getmtime(real_file_path), real_root_path
            
    except (ValueError, OSError):
        # 如果无法获取相对路径或修改时间
        return "Unknown", None, None

def find_xmls_cn_directory(mod_folder_path):
    """在模组文件夹中查找xmls/cn目录"""
    if not mod_folder_path or not os.path.exists(mod_folder_path):
        return None
    
    # 直接构造xmls/cn路径
    xmls_cn_path = os.path.join(mod_folder_path, "xmls", "cn")
    
    if os.path.exists(xmls_cn_path) and os.path.isdir(xmls_cn_path):
        return xmls_cn_path
    
    return None

def parse_name_from_xmls(name_id, xmls_cn_directory):
    """从xmls/cn目录的.xml文件中解析name_id对应的文本"""
    if not xmls_cn_directory or not os.path.exists(xmls_cn_directory):
        return None
    
    # 收集xmls/cn目录下所有.xml文件
    xml_files = []
    for file in os.listdir(xmls_cn_directory):
        if file.lower().endswith('.xml'):
            xml_files.append(os.path.join(xmls_cn_directory, file))
    
    # 检查.xml文件数量
    if len(xml_files) == 0:
        return None
    elif len(xml_files) > 1:
        print(f"警告: 在{xmls_cn_directory}中发现多个.xml文件，跳过名称解析")
        return None
    
    # 只有一个.xml文件，解析它
    xml_file = xml_files[0]
    try:
        # 使用不同的方法解析XML文件
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 方法1: 直接使用正则表达式查找
        # 匹配格式: <text id="ID">文本</text>
        pattern = rf'<text\s+id="{re.escape(name_id)}"[^>]*>([^<]+)</text>'
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
        
        # 方法2: 尝试使用xml.etree.ElementTree解析
        try:
            # 移除可能存在的BOM
            if content.startswith('\ufeff'):
                content = content[1:]
            
            root = ET.fromstring(content)
            
            # 查找所有text元素
            for elem in root.iter():
                if elem.tag == 'text' and elem.get('id') == name_id:
                    text = elem.text
                    return text.strip() if text else None
        except ET.ParseError:
            # XML解析失败，尝试其他方法
            pass
        
        # 方法3: 使用更简单的正则表达式查找
        # 匹配任意元素的id属性
        pattern2 = rf'<[^>]+\s+id="{re.escape(name_id)}"[^>]*>([^<]+)</[^>]+>'
        match2 = re.search(pattern2, content)
        if match2:
            return match2.group(1).strip()
        
    except Exception as e:
        # 静默处理解析错误
        pass
    
    return None

def extract_weapon_info(file_path, root_path):
    """从文件中提取weapon信息"""
    weapons = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        # 使用正则表达式匹配weapon块
        weapon_pattern = r'<equipment\s+id="([^"]*)"\s+type="weapon">(.*?)</equipment>'
        weapon_matches = re.findall(weapon_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # 获取模组文件夹和修改时间
        mod_folder, mod_time, mod_folder_path = get_mod_folder_and_time(file_path, root_path)
        
        # 截取模组文件夹名前15位
        short_mod_name = mod_folder[:15] if mod_folder else "Unknown"
        
        # 查找xmls/cn目录
        xmls_cn_directory = find_xmls_cn_directory(mod_folder_path) if mod_folder_path else None
        
        for weapon_id, weapon_content in weapon_matches:
            # 在weapon内容中查找range, attackSpeed, grade, name
            range_match = re.search(r'<range>([^<]*)</range>', weapon_content, re.IGNORECASE)
            attack_speed_match = re.search(r'<attackSpeed>([^<]*)</attackSpeed>', weapon_content, re.IGNORECASE)
            grade_match = re.search(r'<grade>([^<]*)</grade>', weapon_content, re.IGNORECASE)
            name_match = re.search(r'<name>([^<]*)</name>', weapon_content, re.IGNORECASE)
            
            range_value = range_match.group(1).strip() if range_match else "N/A"
            attack_speed_value = attack_speed_match.group(1).strip() if attack_speed_match else "N/A"
            grade_value = grade_match.group(1).strip() if grade_match else "N/A"
            name_id = name_match.group(1).strip() if name_match else "N/A"
            
            # 映射等级
            mapped_grade = map_grade(grade_value)
            
            # 从xmls/cn目录解析name
            weapon_name = name_id  # 默认使用name_id
            if name_id != "N/A" and xmls_cn_directory:
                parsed_name = parse_name_from_xmls(name_id, xmls_cn_directory)
                if parsed_name:
                    weapon_name = parsed_name
                    # 对于测试目的，可以打印一下找到的名称
                    if "Depression_Weapon_Name" in name_id:
                        print(f"调试: 找到名称 '{parsed_name}' 对应 ID '{name_id}'")
            
            # 格式化修改时间
            mod_time_str = ""
            if mod_time:
                try:
                    mod_time_str = datetime.fromtimestamp(mod_time).strftime('%m-%d %H:%M')
                except:
                    mod_time_str = ""
            
            weapons.append({
                'id': weapon_id.strip(),
                'name': weapon_name,
                'range': range_value,
                'attackSpeed': attack_speed_value,
                'grade': mapped_grade,
                'mod_folder': short_mod_name,
                'mod_time': mod_time,
                'mod_time_str': mod_time_str,
                'name_id': name_id  # 保留原始的name_id用于调试
            })
            
    except Exception as e:
        # 静默处理所有错误
        pass
    
    return weapons

def get_display_width(text):
    """计算字符串在控制台中的显示宽度"""
    if text is None:
        return 0
        
    width = 0
    for char in str(text):
        # 中文字符通常占2个英文字符宽度
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def pad_text(text, width):
    """将文本填充到指定宽度，考虑中英文字符宽度差异"""
    if text is None:
        text = ""
    text = str(text)
    current_width = get_display_width(text)
    if current_width >= width:
        return text
    return text + ' ' * (width - current_width)

def main():
    # 获取当前目录并解析符号链接
    root_dir = get_search_root_from_config()
    real_root_dir = resolve_symlink(root_dir)
    
    print(f"原始目录: {root_dir}")
    print(f"真实目录: {real_root_dir}")
    print("正在搜索武器信息...")
    print("仅处理 .txt 和 .xml 文件，跳过 BaseEquipment.txt")
    print("将从xmls/cn目录解析武器名称")
    print("-" * 120)
    
    all_weapons = []
    processed_files = 0
    
    # 递归遍历所有文件和子目录，跟随符号链接
    for root, dirs, files in os.walk(real_root_dir, followlinks=True):
        # 跳过 .git 目录以提高性能
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # 检查是否应该处理该文件
            if should_process_file(file_path):
                weapons = extract_weapon_info(file_path, real_root_dir)
                if weapons:
                    all_weapons.extend(weapons)
                    processed_files += 1
    
    print(f"处理了 {processed_files} 个文件，找到 {len(all_weapons)} 个武器")
    print()
    
    if not all_weapons:
        print("在指定文件类型中未找到武器。")
        return
    
    # 按模组文件夹修改时间排序（越早修改的越靠前）
    all_weapons.sort(key=lambda x: (x['mod_time'] if x['mod_time'] is not None else float('inf'), x['mod_folder']))
    
    # 打印表头
    mod_header = pad_text("模组", 20)
    time_header = pad_text("修改时间", 12)
    id_header = pad_text("ID", 15)
    name_header = pad_text("武器名称", 25)
    grade_header = pad_text("等级", 8)
    attack_speed_header = pad_text("攻击速度", 12)
    range_header = pad_text("攻击距离", 8)
    
    print(f"{mod_header}{time_header}{id_header}{name_header}{grade_header}{attack_speed_header}{range_header}")
    print("-" * 120)
    
    # 打印每个weapon的信息
    for weapon in all_weapons:
        mod_field = pad_text(weapon['mod_folder'], 20)
        time_field = pad_text(weapon['mod_time_str'], 12)
        id_field = pad_text(weapon['id'], 15)
        name_field = pad_text(weapon['name'], 25)
        grade_field = pad_text(weapon['grade'], 8)
        attack_speed_field = pad_text(weapon['attackSpeed'], 12)
        range_field = pad_text(weapon['range'], 8)
        
        print(f"{mod_field}{time_field}{id_field}{name_field}{grade_field}{attack_speed_field}{range_field}")

if __name__ == "__main__":
    main()