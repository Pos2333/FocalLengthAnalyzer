import os
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from PIL.ExifTags import TAGS
import datetime

class FocalLengthAnalyzer:

    # 创建时间戳文件夹名
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = os.path.join('outputs', timestamp)

    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)

    def __init__(self, input_folder):
        self.input_folder = input_folder
        self.crop_factors = self._load_crop_factors()
        self.focal_groups = self._define_focal_groups()
        self.missing_exif_data = self._load_missing_exif_data()

    #从json配置文件加载常见相机的裁切系数
    def _load_crop_factors(self):
        try:
            with open('camera_crop_factors.json', 'r', encoding='utf-8') as f:
                return json.load(f)  
        except Exception as e:
            print(f"加载裁切系数配置文件失败：{e}")
    
    #从json配置文件加载手动输入的exif数据
    def _load_missing_exif_data(self):
        try:
            with open('missing_exif_data.json', 'r', encoding='utf-8') as f:
                return json.load(f) 
        except Exception as e:
            print(f"加载缺失exif数据失败:{e}")
            return {}
        
    #保存手动输入exif数据到json文件
    def save_missing_exif_data(self):
        try:
            with open('missing_exif_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.missing_exif_data, f, ensure_ascii=False, indent=2)
            print("缺失EXIF数据已保存到 missing_exif_data.json")
        except Exception as e:
            print(f"保存缺失EXIF数据失败: {e}")

    
    #定义焦段分组
    def _define_focal_groups(self):
        return {
            '超广角(14-19mm)': (14, 19),
            '超广角(20-23mm)':(20,23),
            '广角 (24-28mm)': (24, 28),
            '标准广角 (35mm)': (30, 40),
            '标准 (50mm)': (45, 58),
            '人像 (85mm)': (75, 90),
            '中长焦 (100-135mm)': (95, 140),
            '长焦 (200mm)': (150, 250),
            '超长焦 (300mm)': (280, 350),
            '超长焦 (400mm)': (380, 450),
            '超长焦 (500-600mm)': (480, 650),
            '超长焦 (600mm+)': (650, 2000)
        }
    
    #根据相机型号获取裁切系数
    def get_camera_crop_factor(self, camera_model):
        if not camera_model:    #逻辑待修改，改为补充裁切系数但不补充焦段信息
            return 1

        camera_model_lower = camera_model.lower().strip()

        if camera_model_lower in self.crop_factors:
            return self.crop_factors[camera_model_lower]
        
        return 1    # 默认返回1.0
    
    #提取图片的EXIF数据
    def extract_exif_data(self, image_path):
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if exif_data is None:
                    return None, None
                
                exif = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value
                
                # 获取焦段
                focal_length = exif.get('FocalLength')
                if focal_length:
                    if isinstance(focal_length, tuple) and len(focal_length) == 2:
                        focal_length = focal_length[0] / focal_length[1]
                
                # 获取相机型号
                camera_model = exif.get('Model')
                
                return focal_length, camera_model
                
        except Exception as e:
            print(f"读取 {image_path} 的EXIF数据时出错: {e}")
            return None, None
    
    #转换为35mm等效焦段
    def convert_to_35mm_equivalent(self, focal_length, camera_model, sensor_size=None):
        if focal_length is None:
            return None
            
        crop_factor = self.get_camera_crop_factor(camera_model)
        equivalent_focal = focal_length * crop_factor

        return round(equivalent_focal, 1)
    
    #将焦段分配到对应的分组
    def group_focal_length(self, focal_length):
        if focal_length is None:
            return "未知焦段"
            
        for group_name, (min_f, max_f) in self.focal_groups.items():
            if min_f <= focal_length <= max_f:
                return group_name
        
        # 如果不在预定义分组中，返回最接近的整数焦段
        return f"{int(round(focal_length))}mm"
    
    #处理缺失EXIF数据的图片
    def handle_missing_exif(self, image_path):

        filename = os.path.basename(image_path)
        # 检查是否已有保存的数据
        if filename in self.missing_exif_data:
            print(f"\n图片 {filename} 使用之前保存的数据")
            data = self.missing_exif_data[filename]
            return data['equivalent_focal']

        print(f"\n图片 {os.path.basename(image_path)} 缺少EXIF数据")
        print("请手动输入焦段信息:")
        
        while True:
            try:
                focal_input = input("焦段 (mm): ").strip()
                if focal_input:
                    focal_length = float(focal_input)
                    break
                else:
                    print("焦段不能为空，请重新输入")
            except ValueError:
                print("请输入有效的数字")
        
        print("请选择传感器尺寸:")
        print("1. 全画幅 (裁切系数 1.0)")
        print("2. APS-C (裁切系数 1.5)")
        print("3. APS-C (裁切系数 1.6 - 佳能)")
        print("4. M43 (裁切系数 2.0)")
        print("5. 1英寸 (裁切系数 2.7)")
        
        sensor_choice = input("请选择 (1-5, 默认1): ").strip()
        crop_factors = {'1': 1.0, '2': 1.5, '3': 1.6, '4': 2.0, '5': 2.7}
        crop_factor = crop_factors.get(sensor_choice, 1.0)
        
        equivalent_focal = focal_length * crop_factor

            # 保存用户输入
        self.missing_exif_data[filename] = {
            'focal_length': focal_length,
            'crop_factor': crop_factor,
            'equivalent_focal': equivalent_focal,
            'sensor_choice': sensor_choice,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.save_missing_exif_data() 
        
        return equivalent_focal
    
    #分析文件夹中的所有图片
    def analyze_folder(self):
        supported_formats = {'.jpg', '.jpeg', '.tiff', '.tif', '.png', '.arw', '.cr2', '.nef'}
        focal_data = []
        missing_exif_files = []
        
        print("开始分析图片EXIF数据...")
        
        for filename in os.listdir(self.input_folder):
            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext in supported_formats:
                image_path = os.path.join(self.input_folder, filename)
                print(f"处理: {filename}")
                
                focal_length, camera_model = self.extract_exif_data(image_path)
                
                if focal_length is None:
                    missing_exif_files.append(image_path)
                    continue
                
                equivalent_focal = self.convert_to_35mm_equivalent(focal_length, camera_model)
                focal_group = self.group_focal_length(equivalent_focal)
                
                focal_data.append({
                    'filename': filename,
                    'original_focal': focal_length,
                    'camera_model': camera_model,
                    'equivalent_focal': equivalent_focal,
                    'focal_group': focal_group
                })
        
        # 处理缺失EXIF数据的文件
        if missing_exif_files:
            print(f"\n发现 {len(missing_exif_files)} 个文件缺少EXIF数据")
            for image_path in missing_exif_files:
                equivalent_focal = self.handle_missing_exif(image_path)
                focal_group = self.group_focal_length(equivalent_focal)
                
                focal_data.append({
                    'filename': os.path.basename(image_path),
                    'original_focal': None,
                    'camera_model': '手动输入',
                    'equivalent_focal': equivalent_focal,
                    'focal_group': focal_group
                })
            
        return focal_data
    
    #生成统计结果
    def generate_statistics(self, focal_data):
        if not focal_data:
            print("没有找到可分析的图片数据")
            return None
        
        df = pd.DataFrame(focal_data)
        
        # 按焦段分组统计
        group_stats = df['focal_group'].value_counts().sort_index()
        
        # 按具体焦段统计
        focal_stats = df['equivalent_focal'].value_counts().sort_index()
        
        return {
            'dataframe': df,
            'group_stats': group_stats,
            'focal_stats': focal_stats,
            'total_images': len(focal_data)
        }
    
    #可视化统计结果
    def visualize_results(self, stats):
        if not stats:
            return
        
        df = stats['dataframe']
        group_stats = stats['group_stats']
        
        # 设置字体
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'Microsoft YaHei'] 
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 焦段分组饼图
        colors = plt.cm.Set3(np.linspace(0, 1, len(group_stats)))
        wedges, texts, autotexts = ax1.pie(group_stats.values, labels=group_stats.index, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        # 美化饼图文字
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
        
        ax1.set_title('焦段使用分布（分组）', fontsize=14, fontweight='bold')
        
        # 具体焦段柱状图
        focal_counts = df['equivalent_focal'].value_counts().head(15)  # 显示前15个最常用焦段
        bars = ax2.bar(range(len(focal_counts)), focal_counts.values, color='skyblue', alpha=0.7)
        ax2.set_xlabel('等效焦段 (mm)')
        ax2.set_ylabel('使用次数')
        ax2.set_title('最常用焦段排名', fontsize=14, fontweight='bold')
        ax2.set_xticks(range(len(focal_counts)))
        ax2.set_xticklabels([f"{focal}mm" for focal in focal_counts.index], rotation=45)
        
        # 在柱状图上显示数值
        for bar, count in zip(bars, focal_counts.values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(FocalLengthAnalyzer.output_dir, 'focal_length_analysis.png'), dpi=300, bbox_inches='tight')
        plt.show()
    
    #打印统计结果
    def print_statistics(self, stats):
        if not stats:
            return
        
        print("\n" + "="*50)
        print("       焦段使用统计结果")
        print("="*50)
        
        df = stats['dataframe']
        group_stats = stats['group_stats']
        focal_stats = stats['focal_stats']
        
        print(f"总图片数量: {stats['total_images']}")
        print(f"不同焦段分组数量: {len(group_stats)}")
        print(f"不同具体焦段数量: {len(focal_stats)}")
        
        print("\n焦段分组统计:")
        print("-" * 30)
        for group, count in group_stats.items():
            percentage = (count / stats['total_images']) * 100
            print(f"{group:<20} {count:>4}张 ({percentage:>5.1f}%)")
        
        print("\n最常用具体焦段 (前10):")
        print("-" * 30)
        top_focals = focal_stats.head(10)
        for focal, count in top_focals.items():
            percentage = (count / stats['total_images']) * 100
            print(f"{focal:>5}mm {count:>4}张 ({percentage:>5.1f}%)")
        
        # 给出升级建议
        most_used_group = group_stats.index[0]
        most_used_focal = focal_stats.index[0]
        
        print(f"\n升级建议:")
        print(f"• 您最常使用的焦段分组是: {most_used_group}")
        print(f"• 您最常使用的具体焦段是: {most_used_focal}mm")
        print(f"• 建议优先考虑升级 {most_used_group} 范围的镜头")
        
        # 保存详细数据到CSV
        df.to_csv(os.path.join(FocalLengthAnalyzer.output_dir, 'focal_length_details.csv'), index=False, encoding='utf-8-sig')
        print(f"\n详细数据已保存到: focal_length_details.csv")
        print(f"可视化图表已保存到: focal_length_analysis.png")

def main():
    input_folder = 'input_photos'
    
    # 创建分析器并执行分析
    analyzer = FocalLengthAnalyzer(input_folder)
    focal_data = analyzer.analyze_folder()
    
    if not focal_data:
        print("没有找到可分析的图片文件")
        return
    
    # 生成统计结果
    stats = analyzer.generate_statistics(focal_data)
    
    # 显示结果
    analyzer.print_statistics(stats)
    analyzer.visualize_results(stats)

if __name__ == "__main__":
    main()