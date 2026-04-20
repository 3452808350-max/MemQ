#!/usr/bin/env python3
"""
MemQ 质量评分系统 - 在真实数据上测试原版 vs 改进版
"""

import json
import re
from collections import Counter

# ========== 原版 MemQ 评分 ==========

STOPWORDS_ZH = set('的了吗是和在了有就这以个不我们要可以后上为也你他都吧嘛呢没还又着那从好没自己吗到最她他让用能做对没小可大没太')

TEMPLATE_PATTERNS = ['有人提到', '但不是用于', '类似的', '方案']

def memq_original_score(text):
    """原版 MemQ 质量评分"""
    score = 1.0
    
    # 1. Type Weight (基于类别，这里用启发式)
    if any(kw in text for kw in ['完成', '测试', '准确率', '版本']):
        score *= 1.0  # knowledge
    elif any(kw in text for kw in ['待办', '计划', '决定']):
        score *= 0.9  # decision
    elif '```' in text or 'def ' in text:
        score *= 0.85  # code
    else:
        score *= 0.8  # conversation
    
    # 2. Template Factor (噪声检测)
    if any(p in text for p in TEMPLATE_PATTERNS):
        score *= 0.6
    
    # 3. Entity Factor
    entities = len(re.findall(r'[A-Z]{2,}', text))  # 大写缩写
    entities += len(re.findall(r'[\u4e00-\u9fa5]{4,}', text))  # 中文词组
    if entities >= 3:
        score *= 1.2
    elif entities >= 1:
        score *= 1.0
    else:
        score *= 0.8
    
    # 4. Length Factor
    length = len(text)
    if length < 10:
        score *= 0.5
    elif length < 20:
        score *= 0.8
    elif length > 100:
        score *= 1.1
    
    # 5. Stopwords Factor
    tokens = list(text)
    stop_count = sum(1 for t in tokens if t in STOPWORDS_ZH)
    if len(tokens) > 0:
        stop_ratio = stop_count / len(tokens)
        if stop_ratio > 0.5:
            score *= 0.7
    
    # 6. Metadata Factor (简化)
    score *= 1.0
    
    return round(score, 3)


# ========== 改进版评分 ==========

def _detect_negation_type(text):
    """
    检测否定类型
    返回：'contrastive' (对比知识，有价值), 'pure' (纯否定，噪声), 'none' (无否定)
    """
    # 替代方案关键词
    alternative_indicators = ['改用', '换成', '替代', '替换', '改为', '改成', '而是']
    has_alternative = any(kw in text for kw in alternative_indicators)
    
    # 价值比较关键词
    comparison_indicators = ['更', '更好', '更优', '最优', '提升', '提高', '稳定']
    has_comparison = any(kw in text for kw in comparison_indicators)
    
    # 转折词
    contrast_words = ['但', '但是', '然而']
    has_contrast = any(kw in text for kw in contrast_words)
    
    # 否定词
    negation_words = ['不', '没', '未', '非']
    has_negation = any(kw in text for kw in negation_words)
    
    # 纯否定明确短语
    pure_phrases = ['不是用于', '没有采用', '未使用', '未']
    is_pure_phrase = any(p in text for p in pure_phrases)
    
    if not has_negation:
        return 'none'
    
    # 对比知识：有替代方案 OR (转折 + 价值比较)
    if has_alternative:
        return 'contrastive'
    
    if has_contrast and has_comparison:
        return 'contrastive'
    
    # 纯否定
    if is_pure_phrase:
        return 'pure'
    
    return 'pure'


def memq_improved_score(text):
    """改进版 MemQ 质量评分 v3"""
    score = 1.0
    
    # 1. 信息密度 = 实体数 / 总词数
    words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
    entities = len(re.findall(r'[A-Z]{2,}|[\u4e00-\u9fa5]{4,}', text))
    entity_density = entities / len(words) if words else 0
    score *= min(1.0 + entity_density, 1.5)
    
    # 2. 模糊词惩罚 - 检测低信息词
    vague_words = ['一下', '一些', '可能', '也许', '差不多', '大概', '看了', '搞了', '弄了', '做了']
    vague_count = sum(1 for vw in vague_words if vw in text)
    if vague_count > 0:
        score *= (0.7 ** vague_count)
    
    # 3. 否定模式检测 v3
    negation_type = _detect_negation_type(text)
    if negation_type == 'contrastive':
        score *= 1.1  # 对比知识，奖励
    elif negation_type == 'pure':
        score *= 0.7  # 纯否定，惩罚
    
    # 4. 内容词比例
    content_indicators = ['完成', '实现', '测试', '准确', '版本', '数据', '项目', '代码', '系统', '功能']
    content_count = sum(1 for kw in content_indicators if kw in text)
    content_ratio = content_count / len(words) if words else 0
    score *= min(1.0 + content_ratio * 2, 1.3)
    
    # 5. 长度归一化
    if len(text) < 30:
        score *= 0.8
    elif len(text) > 200:
        if entity_density < 0.1:
            score *= 0.9
    
    # 6. 结构质量
    if '```' in text or '├──' in text or '│' in text:
        score *= 1.15
    
    return round(score, 3)


# ========== 测试与对比 ==========

def evaluate_scores(dataset_path):
    with open(dataset_path, 'r') as f:
        memories = json.load(f)
    
    results = []
    for mem in memories:
        text = mem['text']
        category = mem['category']
        
        orig_score = memq_original_score(text)
        impr_score = memq_improved_score(text)
        
        results.append({
            'text': text[:100],
            'category': category,
            'original': orig_score,
            'improved': impr_score,
            'diff': round(impr_score - orig_score, 3)
        })
    
    return results

def analyze_by_category(results):
    from collections import defaultdict
    
    by_cat = defaultdict(lambda: {'original': [], 'improved': []})
    
    for r in results:
        cat = r['category']
        by_cat[cat]['original'].append(r['original'])
        by_cat[cat]['improved'].append(r['improved'])
    
    print('\n=== 各类别平均分 ===')
    print(f'{"Category":<15} {"Original":<10} {"Improved":<10} {"Diff":<10}')
    print('-' * 50)
    
    for cat in ['knowledge', 'decision', 'code', 'conversation']:
        if cat in by_cat:
            orig_avg = sum(by_cat[cat]['original']) / len(by_cat[cat]['original'])
            impr_avg = sum(by_cat[cat]['improved']) / len(by_cat[cat]['improved'])
            print(f'{cat:<15} {orig_avg:<10.3f} {impr_avg:<10.3f} {impr_avg-orig_avg:+.3f}')

def show_top_differences(results, n=10):
    # 改进版比原版高最多的
    improved_better = sorted(results, key=lambda x: x['diff'], reverse=True)[:n]
    
    print(f'\n=== 改进版显著提升的案例 (Top {n}) ===')
    for r in improved_better:
        print(f"\n[{r['category']}] diff={r['diff']:+.3f}")
        print(f"  原版: {r['original']:.3f} | 改进: {r['improved']:.3f}")
        print(f"  文本: {r['text'][:80]}...")
    
    # 改进版比原版低最多的
    improved_worse = sorted(results, key=lambda x: x['diff'])[:n]
    
    print(f'\n=== 改进版显著降低的案例 (Top {n}) ===')
    for r in improved_worse:
        print(f"\n[{r['category']}] diff={r['diff']:+.3f}")
        print(f"  原版: {r['original']:.3f} | 改进: {r['improved']:.3f}")
        print(f"  文本: {r['text'][:80]}...")

def main():
    print('MemQ 质量评分对比测试')
    print('=' * 50)
    
    results = evaluate_scores('/home/kyj/.openclaw/workspace/memq_dataset.json')
    
    print(f'\n总样本数: {len(results)}')
    
    analyze_by_category(results)
    show_top_differences(results, 5)
    
    # 保存结果
    with open('/home/kyj/.openclaw/workspace/memq_comparison.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print('\n\n完整结果已保存到 memq_comparison.json')

if __name__ == '__main__':
    main()
