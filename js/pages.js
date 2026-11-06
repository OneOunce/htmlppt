/* 分页清单 —— 由 generate_index.py 整份生成，请勿手改。
   数据来源：pages/ 目录下的文件名（序号-页名.html，序号位数不限、可以有空号）。
   重新生成：python generate_index.py
   排序：按序号的数值升序；显示用的序号是数组下标（1、2、3…），与文件名编号无关。 */

const SLIDE_PAGES = [
  { "file": "slide-1.html", "title": "欢迎使用 PPT‑style HTML" },
  { "file": "slide-2.html", "title": "第二张幻灯片" },
  { "file": "slide-3.html", "title": "第三张幻灯片" },
  { "file": "slide-4.html", "title": "第4张幻灯片" }
];
const slideFiles  = SLIDE_PAGES.map(function (p) { return p.file; });
const slideTitles = SLIDE_PAGES.map(function (p) { return p.title; });
