from datetime import datetime
import time
import psycopg2
from DrissionPage import ChromiumPage, ChromiumOptions
from openai import OpenAI


client = OpenAI(
    api_key="sk-d84933834d374be9a7d814d79cbcad6e",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)



conn = psycopg2.connect(
            host="192.168.110.54",
            port="5432",
            database="overlord_db",
            user="user1",
            password="user555Y1"
        )
cursor = conn.cursor()

    # start_url = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=date-desc-rank&page=4&crid=YLBANN75IKXD&qid=1767338235&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_pg_4"
new_arrival_start_url = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=date-desc-rank&crid=YLBANN75IKXD&qid=1767337140&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_pg_1"
best_seller_start_url = "https://www.amazon.com/s?k=Shirt&i=fashion-novelty&s=exact-aware-popularity-rank&crid=YLBANN75IKXD&qid=1767339117&sprefix=shirt%2Cfashion-novelty%2C462&xpid=BnGJNx0oBq0gz&ref=sr_st_exact-aware-popularity-rank&ds=v1%3AbGTG%2BvBKF3pkdWNuMKjeKqkR0rIwAXLQF%2BFxvBE96BY"
driver = ChromiumPage()
title_list = []


def recognize_text_from_title(title):
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "user",
                    "content": f""""Please extract the core thematic phrase from the product title following these rules:
                            1. **Structural Analysis**:
                            - Focus on phrases near product terms but exclude the product word itself
                            - Ignore product types (Hat/Cap), audiences (Men/Women), colors, materials,specifications and printing-related terms(Print/Printing)
                            2. **Cultural/Linguistic Features**:
                            - Preserve complete emotional expressions or humorous phrases
                            - Maintain cultural references/puns in their original phrase structures
                            3. **Selection Criteria**:
                            - When multiple candidates exist:
                            a) Choose longer phrases
                            b) Prioritize semantically concrete/complete expressions
                            c) Prefer complete sentence segments
                            4. **Final Validation**:
                            - Remove any remaining product terms before output
                            Examples:
                            Title: The Sao Tome and Principe Flag and Freedom Baseball Cap for Men Women Adjustable Breathable Mesh Trucker Hat Unisex
                            Extract: The Sao Tome and Principe Flag and Freedom

                            Title: Nufar I Don't Need Therapy I Have My Sister 11oz Fun Coffee Mugs Novelty Ceramics Cup
                            Extract: I Don't Need Therapy I Have My Sister
                            Now process this title: {title}
                            Output only the final English phrase without explanations"""
                }
            ]
        )
        subject = response.choices[0].message.content
        subject = subject.replace("'","''")
        return subject
    except Exception as e:
        print(f"API调用出错: {e}")
        return "识别失败"

def translate_subject(subject):
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "user",
                    "content": f""""# 角色设定
你是一位专业的亚马逊电商运营专家，专门负责产品主题标签的本地化翻译。

# 任务说明
请将以下亚马逊产品主题标签/关键词从英文翻译成中文。这些通常是：
- 产品主题标签（如节日、季节、活动主题）
- 产品风格关键词
- 目标人群标签
- 使用场景标签

# 翻译原则

## 核心要求：
1. **保持简洁**：中文表达要简短有力，控制在3-10个字
2. **准确传达主题**：完整表达原文的主题概念
3. **符合中文标签习惯**：使用中文用户熟悉的表达方式
4. **保留关键信息**：不丢失任何重要的主题元素

## 具体规则：

### A. 节日/季节主题：
- 准确翻译节日名称
- 保留节日氛围
- 符合中文节日表达习惯
- 例如：Valentine's Day → 情人节主题

### B. 情感/风格主题：
- 准确传达情感色彩
- 使用地道中文表达
- 保持风格一致性
- 例如：Romantic Love → 浪漫爱情

### C. 事件/活动主题：
- 准确翻译事件名称
- 保留事件特殊性
- 添加"主题"或"风格"后缀（如适用）
- 例如：Super Bowl → 超级碗主题

### D. 人群/场景主题：
- 准确描述目标人群
- 清晰表达使用场景
- 使用市场常用术语

## 翻译示例参考：

### 输入示例：
1. "Christmas Family Reunion Theme"
2. "Beach Summer Vacation Style"
3. "Gamer RGB Lighting Setup"
4. "Office Professional Business"

### 输出示例：
1. "圣诞家庭团圆主题"
2. "海滩夏日度假风"
3. "游戏玩家RGB光效"
4. "办公商务专业款"

## 特别注意：
1. **专有名词处理**：
   - 球队名、赛事名：保留核心意思，简短翻译
   - 地名：标准中文译名
   - 品牌名：一般不翻译

2. **文化适配**：
   - 西方节日要准确但符合中文习惯
   - 体育赛事用中国用户熟悉的表达
   - 避免直译造成的生硬感

3. **格式要求**：
   - 每行一个翻译结果
   - 不加引号
   - 不加解释说明
   - 保持原始顺序
   - 不要出现英文
   - 不要出现如 "\\n" 等特殊字符



## 待翻译的主题标签：
{subject}

## 请开始翻译："""
                }
            ]
        )
        result = response.choices[0].message.content
        result = result.replace("\n", "")
        result = result.replace("'", "''")
        return result
    except Exception as e:
        print(f"API调用出错: {e}")
        return "识别失败"


def translate_title(title):
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "user",
                    "content": f"""# 角色设定
你是一名经验丰富的亚马逊跨境电商运营专家，专门负责产品标题的本地化翻译。

# 任务说明
请将以下亚马逊产品标题从英文翻译成中文。这些标题通常包含：
1. 产品类型（T-Shirt, Hoodie, Dress等）
2. 目标人群（Women's, Men's, Kids, Baby等）
3. 设计主题/图案
4. 产品特性（材质、款式、尺寸等）
5. 品牌/授权信息

# 翻译原则

## 核心要求：
1. **信息完整性**：保留原文所有关键信息
2. **准确性第一**：技术规格、尺寸、材质必须100%准确
3. **符合中文标题结构**：使用"人群+主题+特性+产品类型"结构
4. **可读性强**：中文表达自然流畅，符合电商标题习惯

## 具体翻译规范：

### A. 标题结构优化：
英文结构：主题 + 人群 + 特性 + 产品类型
中文结构：人群 + 主题 + 特性 + 产品类型

### B. 人群翻译：
- Women's → 女款/女士
- Men's → 男款/男士  
- Kids → 儿童款/童装
- Baby → 婴儿款/宝宝
- Unisex → 男女通用款

### C. 产品类型翻译：
- T-Shirt → T恤
- Long Sleeve Shirt → 长袖T恤
- V-Neck T-Shirt → V领T恤
- Hoodie → 卫衣/连帽衫
- Dress → 连衣裙
- Top → 上衣

### D. 主题/图案翻译：
- **节日主题**：准确翻译节日名称 + "主题"
- **体育主题**：球队名意译 + 赛事标准译名
- **情感主题**：使用地道中文情感词汇
- **图案描述**：准确描述图案元素和含义

### E. 特性翻译：
- 尺寸：保留数字，准确翻译单位（Years → 岁）
- 颜色：标准颜色名称
- 材质：专业术语准确
- 款式：准确描述款式特点

# 翻译示例：

## 示例1：
**原文**：Couple Cats Pickup Truck Carrying Flowers Valentine Hearts T-Shirt
**分析**：主题(情侣猫皮卡送花情人节爱心) + 产品类型(T恤)
**翻译**：情人节情侣猫咪皮卡送花爱心主题T恤

## 示例2：
**原文**：Women's Miami Hurricanes CFP Semifinal Fiesta Bowl 2026 Green V-Neck T-Shirt
**分析**：人群(女款) + 主题(迈阿密飓风队CFP半决赛嘉年华碗2026) + 特性(绿色V领) + 产品类型(T恤)
**翻译**：女款迈阿密飓风队2026年CFP半决赛嘉年华碗主题绿色V领T恤

## 示例3：
**原文**：Kids St Patricks Day Long Sleeve Shirts 3-7 Years Girls Boys Saint Patricks Day T-Shirt Lucky Shamrock Irish Heart Tops
**分析**：人群(儿童) + 主题(圣帕特里克节) + 特性(3-7岁男女童长袖) + 图案(幸运三叶草爱尔兰爱心) + 产品类型(上衣)
**翻译**：儿童圣帕特里克节主题3-7岁男女童长袖T恤 幸运三叶草爱尔兰爱心图案上衣

# 特别注意：

## 必须保留的信息：
1. ✅ 产品类型（T恤、卫衣等）
2. ✅ 目标人群（女款、男款、儿童款等）
3. ✅ 尺寸规格（3-7 Years → 3-7岁）
4. ✅ 重要年份（2026年）
5. ✅ 关键特性（V领、长袖等）

## 需要准确翻译的术语：
1. **球队/赛事**：
   - Miami Hurricanes → 迈阿密飓风队
   - CFP → 大学橄榄球季后赛
   - Fiesta Bowl → 嘉年华碗
   - Cotton Bowl → 棉花碗

2. **节日名称**：
   - Valentine's Day → 情人节
   - St Patrick's Day → 圣帕特里克节
   - Christmas → 圣诞节
   - Halloween → 万圣节

3. **设计元素**：
   - Shamrock → 三叶草
   - Heart → 爱心
   - Flowers → 花朵
   - Truck → 皮卡/卡车

# 格式要求：
1. 不加引号
2. 直接输出中文标题

# 待翻译标题：
{title}

# 中文标题："""
                }
            ]
        )
        result = response.choices[0].message.content
        result = result.replace("\n", "")
        result = result.replace("'", "''")
        return result
    except Exception as e:
        print(f"API调用出错: {e}")
        return "识别失败"

def get_items_count():
    item_outer_blocks = driver.eles('xpath://div[@role="listitem"]')
    return len(item_outer_blocks)

def get_items_index_list_new_arrival():
    data_index_list = []
    item_outer_blocks = driver.eles('xpath://div[@role="listitem"]')
    for item_outer_block in item_outer_blocks:
        data_index = item_outer_block.attr('data-index')
        data_index_list.append(data_index)
    return data_index_list

def get_items_index_list_best_seller():
    data_index_list = []
    item_outer_blocks = driver.eles('xpath://div[@data-component-type="s-search-result"]')
    for item_outer_block in item_outer_blocks:
        data_index = item_outer_block.attr('data-index')
        data_index_list.append(data_index)
    return data_index_list


def get_exact_item_xpath(index):
    # item_xpath = f'xpath://span[@class="rush-component s-latency-cf-section"]//div[@role="listitem"][{index}]'
    item_xpath = f'xpath://span[@class="rush-component s-latency-cf-section"]//div[@role="listitem" and @data-index="{index}"]'
    # item = driver.ele(item_xpath)
    return item_xpath

def get_title(index):
    title_xpath = get_exact_item_xpath(index) + "//a//h2"
    title = driver.ele(title_xpath)
    title = title.texts()[0]
    title = title.replace("'", "''")
    return title


def get_picture(index):
    picture_xpath = get_exact_item_xpath(index) + "//img"
    picture = driver.ele(picture_xpath)
    return picture.attr('src')

def get_ASIN(index):
    ASIN_xpath = get_exact_item_xpath(index) + '//span[@class="word-title" and text()="ASIN:"]//following-sibling::span[@class="font-weight-b"]'
    ASIN = driver.ele(ASIN_xpath)
    return ASIN.texts()[0]
# print(get_ASIN(get_items_index(1)))


def get_launch_date(index):
    try:
        launch_date_xpath = get_exact_item_xpath(index) + '//span[@class="mr-ext-1 mt-ext-3"]'
        launch_date_info = driver.ele(launch_date_xpath)
        launch_date_info = launch_date_info.texts()[1]
        launch_date = launch_date_info.split('(')[0].replace(' ', '')
        launched_time = launch_date_info.split('(')[1].split(')')[0]
        return str(launch_date), str(launched_time)
    except:
        return None, None
# print(get_launch_date(get_items_index(1)))
# print(get_title(get_items_index(1)))


def get_item_rank(index):
    try:
        rank_xpath = get_exact_item_xpath(index) + '//span[@class="font-weight-b"]/span[contains(@class,"rank-box")]'
        rank = driver.eles(rank_xpath)[0].texts()[0]
        rank = rank.replace('#', '')
        rank = rank.replace(',', '')
        return int(rank)
    except:
        return None

def get_item_rank_category(index):
    try:
        rank_category_xpath = get_exact_item_xpath(index) + '//p[@class="bsr-list-item"][1]/span[contains(@class,"exts-color-blue")]'
        rank_category = driver.eles(rank_category_xpath)[0].texts()[0]
        return rank_category
    except:
        return None


def next_page_button():
    next_page_button = driver.ele('xpath://a[contains(@class,"s-pagination-next")]').click()


def days_to_int(days_str):
    int_days = int(days_str.replace(',', ''))
    return int_days


# print(get_item_rank(get_items_index(1)))


def combined_title_list(index):
    title_list.append(get_title(index))
    return title_list

def created_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def if_record_exist(ASIN,crawl_date):
    query = f"""
    SELECT EXISTS(
        SELECT 1
        FROM product_rank_history
        WHERE product_id = '{ASIN}'
        AND crawl_date = '{crawl_date}'
    )
    """
    cursor.execute(query)
    result = cursor.fetchone()[0] #返回 TRUE OR FALSE
    return result


def save_to_database(title, title_translation, image_url, ASIN, launch_date, launched_time, rank, rank_category, crawl_at, crawl_date, subject, subject_translation,product_type):
    # 处理None值情况
    launch_date_sql = f"'{launch_date}'" if launch_date else 'NULL'
    rank_sql = str(rank) if rank is not None else 'NULL'
    rank_category_sql = f"'{rank_category}'" if rank_category else 'NULL'
    if if_record_exist(ASIN,crawl_date) == False:
        if check_if_Exist_in_AmazonProduct(ASIN) == False:
            #插入amazon_product表
            query_amazon_product = f"""
                    INSERT INTO amazon_product (asin, title, title_translation, subject, subject_translation, image_url, launch_date, created_at,product_type)
                    VALUES ('{ASIN}', '{title}', '{title_translation}', '{subject}', '{subject_translation}', '{image_url}', {launch_date_sql},'{created_time()}', '{product_type}')
            """
            cursor.execute(query_amazon_product)
        query_product_rank_history = f"""
        INSERT INTO product_rank_history (crawl_date, rank, rank_category, crawled_at, product_id)
        VALUES ('{crawl_date}', {rank_sql}, {rank_category_sql}, '{created_time()}', '{ASIN}')
"""
        cursor.execute(query_product_rank_history)
        conn.commit()



def crawl_new_arrival():
    print("正在爬取新品榜")
    driver.get(new_arrival_start_url)
    time.sleep(10)
    for page in range(3):
        print(f"现在开始爬第{page+1}页")
        item_counts = get_items_count()
        data_index_list = get_items_index_list_new_arrival()
        for data_index in data_index_list:
            ASIN = get_ASIN(data_index)
            title = get_title(data_index)
            title_translation = translate_title(title)
            subject = recognize_text_from_title(title)
            subject_translation = translate_subject(subject)
            image_url = get_picture(data_index)
            launch_date, launched_time = get_launch_date(data_index)
            rank = get_item_rank(data_index)
            rank_category = get_item_rank_category(data_index)
            crawl_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            crawl_date = crawl_at.split(' ')[0]
            product_type = 'new_arrival'
            print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                   rank_category, crawl_at, crawl_date, subject, subject_translation, product_type])
            print("保存到数据库")

            save_to_database(title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                                 rank_category, crawl_at, crawl_date, subject, subject_translation, product_type)

            # print([ASIN,title, title_translation, image_url, launch_date, launched_time, rank, rank_category, crawl_at, subject, subject_translation,product_type])
            # combined_title_list(data_index)
        # next_page_button()
        time.sleep(10)

    # next_page_button()
    should_stop_flag = False # 控制是否停止循环

    current_page = 4

    while not should_stop_flag:
        print(f"现在开始爬第{current_page}页")
        item_counts = get_items_count()
        data_index_list = get_items_index_list_new_arrival()

        for cur_index,data_index in enumerate(data_index_list):
            launch_date,launched_time = get_launch_date(data_index)
            if launched_time is None:
                continue
            launched_time = days_to_int(launched_time.split('days')[0])
            print(cur_index, launched_time)


            if launched_time > 1:
                should_stop_flag = True
                print(f"第{current_page}页，第{cur_index+1}个商品，距离发布时间已经超过1天，停止爬取")
                break
            else:
                ASIN = get_ASIN(data_index)
                title = get_title(data_index)
                title_translation = translate_title(title)
                subject = recognize_text_from_title(title)
                subject_translation = translate_subject(subject)
                image_url = get_picture(data_index)
                launch_date, launched_time = get_launch_date(data_index)
                rank = get_item_rank(data_index)
                rank_category = get_item_rank_category(data_index)
                crawl_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                crawl_date = crawl_at.split(' ')[0]
                product_type = 'new_arrival'
                print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                                 rank_category, crawl_at, crawl_date, subject, subject_translation, product_type])
                print("保存到数据库")
                save_to_database(title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                                 rank_category, crawl_at, crawl_date, subject, subject_translation, product_type)

                # combined_title_list(data_index)
        if should_stop_flag:
            break

        current_page = current_page + 1
        next_page_button()
        time.sleep(10)
    conn.commit()
    return title_list

#未完成功能，判断某链接今天是否爬取过
def check_if_crawled_today(asin,scrape_time):
    cursor.execute("SELECT * FROM best_seller WHERE ASIN = %s AND scrape_time = %s", (asin, scrape_time))
    result = cursor.fetchone()
    return result is not None

def check_if_Exist_in_AmazonProduct(ASIN):
    query = f"""
        SELECT EXISTS(
            SELECT 1
            FROM amazon_product
            WHERE asin = '{ASIN}'
        )
        """
    cursor.execute(query)
    result = cursor.fetchone()[0]  # 返回 TRUE OR FALSE
    return result



def crawl_best_seller():
    print("正在爬取新奇特")
    driver.get(best_seller_start_url)
    time.sleep(10)
    for page in range(3):
        print(f"现在开始爬第{page + 1}页")
        item_counts = get_items_count()
        data_index_list = get_items_index_list_best_seller()
        for data_index in data_index_list:
            ASIN = get_ASIN(data_index)
            title = get_title(data_index)
            title_translation = translate_title(title)
            subject = recognize_text_from_title(title)
            subject_translation = translate_subject(subject)
            image_url = get_picture(data_index)
            launch_date, launched_time = get_launch_date(data_index)
            rank = get_item_rank(data_index)
            rank_category = get_item_rank_category(data_index)
            crawl_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            crawl_date = crawl_at.split(' ')[0]
            product_type = "new_peculiar"
            # 保存到数据库
            print("保存到数据库")
            save_to_database(title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                             rank_category, crawl_at, crawl_date, subject, subject_translation, product_type)
            #title, title_translation, image_url, ASIN, launch_date, launched_time, rank, rank_category, crawl_at, crawl_date, subject, subject_translation
            print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank, rank_category, crawl_at, subject, subject_translation,product_type])
            # combined_title_list(data_index)
        next_page_button()
        time.sleep(10)

    # next_page_button()
    should_stop_flag = False  # 控制是否停止循环

    current_page = 4

    while not should_stop_flag:
        print(f"现在开始爬第{current_page}页")
        item_counts = get_items_count()
        data_index_list = get_items_index_list_best_seller()

        for cur_index, data_index in enumerate(data_index_list):
            launch_date, launched_time = get_launch_date(data_index)
            if launched_time is None:
                continue
            launched_time = days_to_int(launched_time.split('days')[0])
            print(cur_index, launched_time)

            if launched_time > 7:
                should_stop_flag = True
                print(f"第{current_page}页，第{cur_index + 1}个商品，距离发布时间已经超过7天，停止爬取")
                break
            else:
                ASIN = get_ASIN(data_index)
                title = get_title(data_index)
                title_translation = translate_title(title)
                subject = recognize_text_from_title(title)
                subject_translation = translate_subject(subject)
                image_url = get_picture(data_index)
                launch_date, launched_time = get_launch_date(data_index)
                rank = get_item_rank(data_index)
                rank_category = get_item_rank_category(data_index)
                crawl_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                crawl_date = crawl_at.split(' ')[0]
                product_type = "new_peculiar"
                # 保存到数据库
                print("保存到数据库")
                save_to_database(title, title_translation, image_url, ASIN, launch_date, launched_time, rank,
                                 rank_category, crawl_at, crawl_date, subject, subject_translation, product_type)
                print([title, title_translation, image_url, ASIN, launch_date, launched_time, rank, rank_category, crawl_at, subject, subject_translation,product_type])
                # combined_title_list(data_index)
        if should_stop_flag:
            break

        current_page = current_page + 1
        next_page_button()
        time.sleep(10)
    conn.commit()
    return title_list



if __name__ == '__main__':
    driver.get(new_arrival_start_url)
    time.sleep(10)
    crawl_best_seller()
    print("新奇特爬取完成")
    time.sleep(600)
    crawl_new_arrival()
    print("新品榜爬取完成")
    conn.close()