import re

with open('web/templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_tags = """\
                            ${diff < -0.04 ? '<span class="text-[8px] bg-emerald-500/20 text-emerald-400 px-1 rounded border border-emerald-500/30">一番時計</span>' : ''}
                            ${p.win_rate > 6.5 ? '<span class="text-[8px] bg-indigo-500/20 text-indigo-400 px-1 rounded border border-indigo-500/30">上位</span>' : ''}
                            ${bi.propeller ? '<span class="text-[8px] bg-orange-500/20 text-orange-400 px-1 rounded border border-orange-500/30">P交換</span>' : ''}
                            ${p.local_win_rate && p.local_win_rate >= 6.0 && (p.local_win_rate - p.win_rate) >= 1.0 ? '<span class="text-[8px] bg-cyan-500/20 text-cyan-400 px-1 rounded border border-cyan-500/30">当地巧者</span>' : ''}
                            ${bi.parts_exchange && bi.parts_exchange !== 'なし' ? `<span class="text-[8px] bg-rose-500/20 text-rose-400 px-1 rounded border border-rose-500/30">${bi.parts_exchange}</span>` : ''}
"""
# Use exact string replacement
old_tags = """\
                            ${diff < -0.04 ? '<span class="text-[8px] bg-emerald-500/20 text-emerald-400 px-1 rounded border border-emerald-500/30">一番時計</span>' : ''}
                            ${p.win_rate > 6.5 ? '<span class="text-[8px] bg-indigo-500/20 text-indigo-400 px-1 rounded border border-indigo-500/30">上位</span>' : ''}
                            ${bi.propeller ? '<span class="text-[8px] bg-orange-500/20 text-orange-400 px-1 rounded border border-orange-500/30">P交換</span>' : ''}
"""
html = html.replace(old_tags, new_tags)

with open('web/templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
