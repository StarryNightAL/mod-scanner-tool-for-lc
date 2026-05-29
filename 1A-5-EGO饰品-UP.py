import os
import re
import json
import glob
from pathlib import Path
import time
import xml.etree.ElementTree as ET

def get_search_root_from_config(default_root=None):
    """从脚本所在目录的config.json中读取target_scan_path，若失败则返回default_root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    if os.path.isfile(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get('target_scan_path')
                if path:
                    if not os.path.isabs(path):
                        path = os.path.join(script_dir, path)
                    return path
        except Exception:
            pass
    return default_root if default_root is not None else os.getcwd()

SEARCH_ROOT = get_search_root_from_config()

# 颜色代码
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

# 要忽略的文件夹
IGNORE_FOLDERS = [
    "ColoredFixerMod-ReturnoftheRedmist-423-2-3-1758101187",
    "TwilightRemakeMod-426-1-2-1758016480",
    "SolemnLamentRemake2.0Mod-570-1-2-1757941956"
]

def get_upstream_folder_mod_time(file_path):
    """获取上游文件夹修改时间"""
    path_parts = Path(file_path).parts
    
    if len(path_parts) > 1:
        if path_parts[0] == '.':
            if len(path_parts) > 1:
                upstream_folder = path_parts[1]
            else:
                upstream_folder = file_path
        else:
            upstream_folder = path_parts[0]
    else:
        upstream_folder = file_path
    
    upstream_abs_path = os.path.abspath(upstream_folder)
    return os.path.getmtime(upstream_abs_path), upstream_folder

def parse_bonus_content(bonus_content):
    """解析bonus内容"""
    attributes = {
        'hp': 0, 'mental': 0, 'workProb': 0, 
        'cubeSpeed': 0, 'movement': 0, 'attackSpeed': 0
    }
    
    for attr in attributes:
        match = re.search(f'<{attr}>(-?\\d+)</{attr}>', bonus_content)
        if match:
            attributes[attr] = int(match.group(1))
    
    return attributes

def extract_attach_pos(equipment_content):
    """提取attachPos值"""
    attach_pos_match = re.search(r'<attachPos>([^<]*)</attachPos>', equipment_content)
    return attach_pos_match.group(1) if attach_pos_match else ""

def extract_attach_type(equipment_content):
    """提取attachType值"""
    attach_type_match = re.search(r'<attachType>([^<]*)</attachType>', equipment_content)
    return attach_type_match.group(1) if attach_type_match else ""

def extract_equipment_name(equipment_content):
    """提取装备名称引用ID"""
    name_match = re.search(r'<name>([^<]*)</name>', equipment_content)
    return name_match.group(1) if name_match else ""

def format_value(value):
    """格式化数值并添加颜色"""
    if value > 0:
        return f"{Colors.CYAN}{value:>5}{Colors.END}"
    elif value < 0:
        return f"{Colors.RED}{value:>5}{Colors.END}"
    else:
        return f"{Colors.WHITE}{value:>5}{Colors.END}"

def should_ignore_file(file_path):
    """检查文件是否在忽略的文件夹中"""
    for ignore_folder in IGNORE_FOLDERS:
        if ignore_folder in file_path:
            return True
    return False

def extract_chinese_name(file_path, name_id):
    """
    从对应XML文件中提取中文名称
    现在需要装备的name_id作为参数
    """
    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        file_dir = os.path.dirname(file_path)
        parent_dir = os.path.dirname(file_dir)
        xml_dir = os.path.join(parent_dir, "xmls", "cn")
        
        if not name_id:
            return "", xml_dir, "no_name_id"
        
        if os.path.exists(xml_dir):
            xml_files = [f for f in os.listdir(xml_dir) if f.endswith(('.xml', '.txt'))]
            
            for xml_file in xml_files:
                xml_path = os.path.join(xml_dir, xml_file)
                try:
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    
                    for elem in root.findall(".//text"):
                        if elem.get('id') == name_id:
                            return elem.text, xml_path, "success"
                    
                    for elem in root.findall(".//text"):
                        elem_id = elem.get('id', '')
                        if name_id in elem_id:
                            return elem.text, xml_path, f"success (partial match: {elem_id})"
                            
                except ET.ParseError:
                    try:
                        with open(xml_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        pattern = f'<text id="{name_id}">([^<]*)</text>'
                        match = re.search(pattern, content)
                        if match:
                            return match.group(1), xml_path, "success (regex)"
                    except:
                        continue
                except Exception:
                    continue
            
            return "", xml_dir, f"name_id_not_found (tried: {', '.join(xml_files)})"
        else:
            return "", xml_dir, "directory_not_found"
                
    except Exception as e:
        return "", "", f"error: {str(e)}"

def extract_equipment_info():
    """递归搜索并提取饰品信息"""
    results = []
    
    patterns = [
        os.path.join(SEARCH_ROOT, "*", "*", "Equipment", "txts", "*.txt"),
        os.path.join(SEARCH_ROOT, "*", "*", "Equipment", "xmls", "cn", "*.txt"),
        os.path.join(SEARCH_ROOT, "*", "Equipment", "txts", "*.xml"),
        os.path.join(SEARCH_ROOT, "*", "Equipment", "xmls", "cn", "*.xml")
    ]
    
    file_paths = []
    for pattern in patterns:
        file_paths.extend(glob.glob(pattern, recursive=True))
    
    file_paths = list(set(file_paths))
    
    file_paths = [f for f in file_paths if not should_ignore_file(f)]
    
    file_paths_with_upstream = []
    for file_path in file_paths:
        upstream_mod_time, upstream_folder = get_upstream_folder_mod_time(file_path)
        file_paths_with_upstream.append((file_path, upstream_mod_time, upstream_folder))
    
    file_paths_with_upstream.sort(key=lambda x: x[1])
    
    file_accessory_count = {}
    
    for file_path, upstream_mod_time, upstream_folder in file_paths_with_upstream:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            equipment_matches = re.findall(
                r'<equipment id="([^"]*)" type="special">(.*?)</equipment>',
                content,
                re.DOTALL
            )
            
            if not equipment_matches:
                continue
            
            file_accessory_count[file_path] = len(equipment_matches)
            
            for equipment_id, equipment_content in equipment_matches:
                name_id = extract_equipment_name(equipment_content)
                chinese_name, xml_path, status = extract_chinese_name(file_path, name_id)
                
                bonus_match = re.search(r'<bonus>(.*?)</bonus>', equipment_content, re.DOTALL)
                if bonus_match:
                    attributes = parse_bonus_content(bonus_match.group(1))
                else:
                    attributes = {'hp': 0, 'mental': 0, 'workProb': 0, 'cubeSpeed': 0, 'movement': 0, 'attackSpeed': 0}
                
                attach_pos = extract_attach_pos(equipment_content)
                attach_type = extract_attach_type(equipment_content)
                
                results.append({
                    'file': file_path,
                    'equipment_id': equipment_id,
                    'name_id': name_id,
                    'attach_pos': attach_pos,
                    'attach_type': attach_type,
                    'attributes': attributes,
                    'chinese_name': chinese_name,
                    'status': status,
                    'upstream_mod_time': upstream_mod_time,
                    'file_accessory_count': file_accessory_count[file_path]
                })
            
            print(f"已处理: {file_path} (找到 {len(equipment_matches)} 个饰品)")
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            continue
    
    results.sort(key=lambda x: x['upstream_mod_time'])
    return results, file_accessory_count

def display_results(results, file_accessory_count):
    """显示结果"""
    print("\n" + "="*120)
    print(f"{Colors.BOLD}饰品详细信息 (按上游文件夹修改时间排序):{Colors.END}")
    print("="*120)
    
    header = f"{Colors.BOLD}{'文件':<25} {'ID':>10} {'位置':>10} {'类型':>8} {'生命':>5} {'精神':>5} {'成功率':>6} {'工作速度':>6} {'攻击速度':>5} {'移动速度':>6}{Colors.END}"
    print(header)
    print("-"*120)
    
    displayed_files = set()
    
    for result in results:
        filename = os.path.basename(result['file'])
        attrs = result['attributes']
        
        if result['file_accessory_count'] > 1 and result['file'] not in displayed_files:
            filename_display = f"{filename} (*{result['file_accessory_count']})"
            displayed_files.add(result['file'])
        else:
            filename_display = filename
        
        colored_filename = f"{Colors.GREEN}{filename_display:<25}{Colors.END}"
        colored_id = f"{Colors.BLUE}{result['equipment_id']:>10}{Colors.END}"
        colored_pos = f"{Colors.YELLOW}{result['attach_pos']:>10}{Colors.END}"
        colored_type = f"{Colors.CYAN}{result['attach_type']:>8}{Colors.END}"
        
        line = f"{colored_filename} {colored_id} {colored_pos} {colored_type} {format_value(attrs['hp'])} {format_value(attrs['mental'])} {format_value(attrs['workProb'])} {format_value(attrs['cubeSpeed'])} {format_value(attrs['attackSpeed'])} {format_value(attrs['movement'])}"
        print(line)
    
    print("\n" + "="*100)
    print(f"{Colors.BOLD}中文名称 (每个饰品):{Colors.END}")
    print("="*100)
    
    chinese_header = f"{Colors.BOLD}{'文件':<25} {'装备ID':<10} {'中文名称':<30} {'状态':<30}{Colors.END}"
    print(chinese_header)
    print("-"*100)
    
    for result in results:
        filename = os.path.basename(result['file'])
        equipment_id = result['equipment_id']
        chinese_name = result['chinese_name']
        status = result['status']
        
        if result['file_accessory_count'] > 1:
            filename_display = f"{filename} (*{result['file_accessory_count']})"
        else:
            filename_display = filename
        
        if chinese_name:
            status_color = Colors.GREEN
        elif "not_found" in status or "error" in status:
            status_color = Colors.RED
        else:
            status_color = Colors.YELLOW
            
        colored_filename = f"{Colors.GREEN}{filename_display:<25}{Colors.END}"
        colored_id = f"{Colors.BLUE}{equipment_id:<10}{Colors.END}"
        colored_chinese = f"{Colors.CYAN}{chinese_name:<30}{Colors.END}" if chinese_name else f"{Colors.WHITE}{'N/A':<30}{Colors.END}"
        colored_status = f"{status_color}{status:<30}{Colors.END}"
        
        print(f"{colored_filename} {colored_id} {colored_chinese} {colored_status}")
    
    multi_accessory_files = {file: count for file, count in file_accessory_count.items() if count > 1}
    if multi_accessory_files:
        print(f"\n{Colors.BOLD}包含多个饰品的文件:{Colors.END}")
        for file_path, count in multi_accessory_files.items():
            filename = os.path.basename(file_path)
            print(f"  {Colors.YELLOW}{filename}: {count} 个饰品{Colors.END}")

def main():
    """主函数"""
    print(f"{Colors.BOLD}搜索饰品文件中...{Colors.END}")
    print("搜索模式:")
    print(f"  {Colors.YELLOW}1. {os.path.join(SEARCH_ROOT, '*/*/Equipment/txts/*.txt')}{Colors.END}")
    print(f"  {Colors.YELLOW}2. {os.path.join(SEARCH_ROOT, '*/*/Equipment/xmls/cn/*.xml')}{Colors.END}")
    print(f"  {Colors.YELLOW}3. {os.path.join(SEARCH_ROOT, '*/Equipment/txts/*.txt')}{Colors.END}")
    print(f"  {Colors.YELLOW}4. {os.path.join(SEARCH_ROOT, '*/Equipment/xmls/cn/*.xml')}{Colors.END}")
    print(f"{Colors.RED}忽略文件夹: {', '.join(IGNORE_FOLDERS)}{Colors.END}")
    print()
    
    results, file_accessory_count = extract_equipment_info()
    
    if not results:
        print(f"{Colors.RED}未找到匹配的饰品!{Colors.END}")
        return
    
    print(f"\n{Colors.GREEN}找到 {len(results)} 个饰品{Colors.END}")
    
    display_results(results, file_accessory_count)
    
    unique_files = len(set(r['file'] for r in results))
    accessories_with_chinese = sum(1 for r in results if r['chinese_name'])
    multi_accessory_files = len([count for count in file_accessory_count.values() if count > 1])
    
    print(f"\n{Colors.BOLD}统计信息:{Colors.END}")
    print(f"  {Colors.WHITE}总饰品数: {len(results)}{Colors.END}")
    print(f"  {Colors.WHITE}涉及文件数: {unique_files}{Colors.END}")
    print(f"  {Colors.WHITE}有中文名称的饰品: {accessories_with_chinese}{Colors.END}")
    print(f"  {Colors.WHITE}无中文名称的饰品: {len(results) - accessories_with_chinese}{Colors.END}")
    print(f"  {Colors.WHITE}包含多个饰品的文件: {multi_accessory_files}{Colors.END}")

if __name__ == "__main__":
    main()