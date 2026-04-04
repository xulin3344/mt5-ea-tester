# Changelog

## v2.0.0 - 2026-04-05
### 核心修复：回测引擎完全跑通
- 修复 subprocess 调用方式，匹配 batch 脚本行为，策略测试器正常弹出
- INI 配置路径改为绝对路径，确保 MT5 正确加载配置
- 修复 INI 编码为 UTF-16 LE（MT5 要求），之前误改 UTF-8 导致解析失败
- INI 添加 Report 字段，回测完成后自动生成报告
- 修复 Settings 页面路径验证功能，显示详细调试信息
- ConfigPage 补充 report_dir 参数传递

## v0.1.0 - 2026-04-04
### 初始版本
- PyQt6 桌面应用框架
- 6 步工作流：设置 / 编译 / 配置 / 回测 / 分析 / 清理
- 实时日志与进度条
- 配置持久化（QSettings）
- HTML 排名报告生成
- PyInstaller 打包为独立 exe
