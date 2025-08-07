#!/usr/bin/env python3
"""
测试continue语句修复的脚本
"""

import sys
sys.path.append('.')
from analysis.cfg import CFG

def test_continue_statement():
    """测试continue语句的控制流是否正确"""
    
    # 测试代码：包含continue语句的循环
    test_code = '''
    int test_continue() {
        int i = 0;
        for (i = 0; i < 10; i++) {
            if (i % 2 == 0) {
                continue;
            }
            printf("%d\n", i);
        }
        return 0;
    }
    '''
    
    print("🔍 测试continue语句的CFG构建...")
    print("="*50)
    
    cfg_analyzer = CFG('c')
    cfgs = cfg_analyzer.see_cfg(test_code, filename='test_continue_cfg', pdf=False, dot_format=False, view=False)
    
    if not cfgs:
        print("❌ CFG构建失败")
        return False
    
    cfg = cfgs[0]
    print(f"✅ CFG构建成功! 节点数: {len(cfg.nodes)}")
    
    # 查找continue节点
    continue_node = None
    for node in cfg.nodes:
        if 'continue' in node.text:
            continue_node = node
            break
    
    if not continue_node:
        print("❌ 未找到continue节点")
        return False
    
    print(f"📍 找到continue节点: {continue_node.id}")
    
    # 检查continue节点的出边
    if continue_node.id in cfg.edges:
        edges = cfg.edges[continue_node.id]
        print(f"🔗 continue节点的出边数量: {len(edges)}")
        
        for edge in edges:
            target_node = None
            for node in cfg.nodes:
                if node.id == edge.id:
                    target_node = node
                    break
            
            if target_node:
                print(f"   -> 目标节点 {edge.id}: {target_node.text[:50]}...")
                
                # 检查目标节点是否是循环体的第一个语句
                if 'for' in target_node.text:
                    print("   ⚠️  continue指向循环条件 (旧行为)")
                elif 'printf' in target_node.text or 'i++' in target_node.text:
                    print("   ✅ continue指向循环体语句 (正确行为)")
                else:
                    print(f"   ℹ️  continue指向: {target_node.text[:30]}...")
    else:
        print("❌ continue节点没有出边")
        return False
    
    return True

def test_user_example():
    """测试用户提供的utf8casecmp函数"""
    
    print("\n🔍 测试用户示例函数...")
    print("="*50)
    
    code = '''
    utf8_constexpr14_impl int utf8casecmp(const utf8_int8_t *src1, 
                                           const utf8_int8_t *src2) { 
       utf8_int32_t src1_lwr_cp = 0, src2_lwr_cp = 0, src1_upr_cp = 0, 
                    src2_upr_cp = 0, src1_orig_cp = 0, src2_orig_cp = 0; 
     
       for (;;) { 
         src1 = utf8codepoint(src1, &src1_orig_cp); 
         src2 = utf8codepoint(src2, &src2_orig_cp); 
     
         src1_lwr_cp = utf8lwrcodepoint(src1_orig_cp); 
         src2_lwr_cp = utf8lwrcodepoint(src2_orig_cp); 
     
         src1_upr_cp = utf8uprcodepoint(src1_orig_cp); 
         src2_upr_cp = utf8uprcodepoint(src2_orig_cp); 
     
         if ((0 == src1_orig_cp) && (0 == src2_orig_cp)) { 
           return 0; 
         } else if ((src1_lwr_cp == src2_lwr_cp) || (src1_upr_cp == src2_upr_cp)) { 
           continue; 
         } 
     
         return src1_lwr_cp - src2_lwr_cp; 
       } 
     } 
    '''
    
    cfg_analyzer = CFG('c')
    cfgs = cfg_analyzer.see_cfg(code, filename='user_example_cfg', pdf=False, dot_format=False, view=False)
    
    if not cfgs:
        print("❌ CFG构建失败")
        return False
    
    cfg = cfgs[0]
    print(f"✅ CFG构建成功! 节点数: {len(cfg.nodes)}")
    
    # 查找continue节点和循环体第一个语句
    continue_node = None
    first_body_node = None
    
    for node in cfg.nodes:
        if 'continue' in node.text:
            continue_node = node
        elif 'utf8codepoint(src1' in node.text:
            first_body_node = node
    
    if not continue_node or not first_body_node:
        print("❌ 未找到关键节点")
        return False
    
    print(f"📍 continue节点: {continue_node.id}")
    print(f"📍 循环体第一个语句: {first_body_node.id}")
    
    # 检查continue是否正确连接到循环体第一个语句
    if continue_node.id in cfg.edges:
        edges = cfg.edges[continue_node.id]
        for edge in edges:
            if edge.id == first_body_node.id:
                print("✅ continue正确连接到循环体第一个语句!")
                return True
    
    print("❌ continue未正确连接到循环体第一个语句")
    return False

if __name__ == "__main__":
    print("🚀 开始测试continue语句修复...")
    print()
    
    success1 = test_continue_statement()
    success2 = test_user_example()
    
    print("\n" + "="*50)
    if success1 and success2:
        print("🎉 所有测试通过! continue语句修复成功!")
    else:
        print("❌ 部分测试失败")
    print("="*50)