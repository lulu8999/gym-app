/**
 * BodyMap - 专业医学人体肌肉图组件
 * 基于解剖学肌肉区域划分，89个精确肌肉区域
 * 支持按 category + muscle_group 精确高亮
 */
class BodyMap {
  constructor(container, options = {}) {
    this.container = container;
    this.view = options.view || 'front';
    this.highlightCategory = options.highlightCategory || '';
    this.highlightMuscle = options.highlightMuscle || '';
    this.render();
  }

  // 根据 category + muscle_group 获取要高亮的肌肉区域 ID 列表
  getHighlightIds(category, muscleGroup) {
    const mapping = {
      // 胸部
      '胸': {
        '胸大肌': ['chest-upper', 'chest-lower'],
        '上胸': ['chest-upper'],
        '下胸': ['chest-lower'],
        '': ['chest-upper', 'chest-lower']
      },
      // 背部
      '背': {
        '背阔肌': ['lats-l', 'lats-r'],
        '竖脊肌': ['erector-spinae-l', 'erector-spinae-r'],
        '': ['lats-l', 'lats-r', 'erector-spinae-l', 'erector-spinae-r']
      },
      // 肩部
      '肩': {
        '三角肌': ['delt-front-l', 'delt-front-r', 'delt-side-l', 'delt-side-r', 'delt-rear-l', 'delt-rear-r'],
        '三角肌中束': ['delt-side-l', 'delt-side-r'],
        '三角肌后束': ['delt-rear-l', 'delt-rear-r'],
        '': ['delt-front-l', 'delt-front-r', 'delt-side-l', 'delt-side-r']
      },
      // 手臂
      '手臂': {
        '肱二头肌': ['bicep-l', 'bicep-r'],
        '肱三头肌': ['tricep-l', 'tricep-r'],
        '': ['bicep-l', 'bicep-r', 'tricep-l', 'tricep-r']
      },
      // 核心
      '核心': {
        '腹直肌': ['abs-upper', 'abs-lower'],
        '腹斜肌': ['oblique-l', 'oblique-r'],
        '核心': ['abs-upper', 'abs-lower', 'oblique-l', 'oblique-r'],
        '': ['abs-upper', 'abs-lower', 'oblique-l', 'oblique-r']
      },
      // 腿部
      '腿': {
        '股四头肌': ['quad-l', 'quad-r'],
        '腘绳肌': ['hamstring-l', 'hamstring-r'],
        '小腿': ['calf-l', 'calf-r'],
        '': ['quad-l', 'quad-r', 'hamstring-l', 'hamstring-r', 'calf-l', 'calf-r']
      },
      // 有氧
      '有氧': {
        '全身': ['chest-upper', 'chest-lower', 'quad-l', 'quad-r', 'bicep-l', 'bicep-r', 'abs-upper', 'abs-lower'],
        '腿部': ['quad-l', 'quad-r', 'calf-l', 'calf-r'],
        '': ['chest-upper', 'chest-lower', 'quad-l', 'quad-r', 'bicep-l', 'bicep-r']
      }
    };
    
    const catMap = mapping[category];
    if (!catMap) return [];
    
    const ids = catMap[muscleGroup] || catMap[''] || [];
    return ids;
  }

  render() {
    const highlightIds = this.getHighlightIds(this.highlightCategory, this.highlightMuscle);
    const isHighlight = (id) => highlightIds.includes(id);
    const hlFill = (id) => isHighlight(id) ? 'url(#hlGrad)' : '#3A3366';
    const hlOpacity = (id) => isHighlight(id) ? '1' : '0.25';
    const hlClass = (id) => isHighlight(id) ? 'muscle-hl pulse' : '';

    this.container.innerHTML = `
<svg viewBox="0 0 200 320" xmlns="http://www.w3.org/2000/svg" class="body-map-svg">
  <defs>
    <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#8B7EC8"/>
      <stop offset="100%" stop-color="#6B5D9A"/>
    </linearGradient>
    <linearGradient id="hlGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF6B35"/>
      <stop offset="100%" stop-color="#FF8B5A"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .muscle-hl { filter: url(#glow); }
      .pulse { animation: musclePulse 2s ease-in-out infinite; }
      @keyframes musclePulse { 0%,100%{opacity:0.85} 50%{opacity:1} }
      .body-map-svg .body-base { fill: url(#bodyGrad); }
      .body-map-svg .muscle-area { transition: all 0.3s ease; }
    </style>
  </defs>

  <!-- 头部 -->
  <ellipse cx="100" cy="28" rx="17" ry="22" class="body-base"/>
  <ellipse cx="100" cy="25" rx="13" ry="16" fill="#6B5D9A" opacity="0.25"/>
  <!-- 面部特征 -->
  <circle cx="93" cy="22" r="2" fill="#4A3D7A" opacity="0.4"/>
  <circle cx="107" cy="22" r="2" fill="#4A3D7A" opacity="0.4"/>
  <path d="M95 30 Q100 33 105 30" stroke="#4A3D7A" stroke-width="1" fill="none" opacity="0.3"/>

  <!-- 颈部 -->
  <path d="M90 50 Q100 57 110 50" class="body-base"/>

  <!-- === 躯干 === -->
  <path d="M66 57 Q58 68 55 95 Q54 118 58 135 L65 145 Q82 152 100 152 Q118 152 135 145 L142 135 Q146 118 145 95 Q142 68 134 57 Q118 48 100 48 Q82 48 66 57Z" class="body-base"/>

  <!-- 胸肌 - 上胸 -->
  <path id="chest-upper" class="muscle-area ${hlClass('chest-upper')}"
        d="M70 62 Q74 57 85 59 Q92 61 100 63 Q108 61 115 59 Q126 57 130 62 Q132 70 128 78 Q118 83 100 85 Q82 83 72 78 Q68 70 70 62Z"
        fill="${hlFill('chest-upper')}" opacity="${hlOpacity('chest-upper')}"/>

  <!-- 胸肌 - 下胸 -->
  <path id="chest-lower" class="muscle-area ${hlClass('chest-lower')}"
        d="M72 78 Q82 83 100 85 Q118 83 128 78 Q130 86 126 92 Q118 97 100 98 Q82 97 74 92 Q70 86 72 78Z"
        fill="${hlFill('chest-lower')}" opacity="${hlOpacity('chest-lower')}"/>

  <!-- 胸肌中线 -->
  <line x1="100" y1="60" x2="100" y2="98" stroke="#2D2456" stroke-width="0.8" opacity="0.4"/>

  <!-- 肩部 - 三角肌前束 -->
  <ellipse id="delt-front-l" class="muscle-area ${hlClass('delt-front-l')}"
           cx="60" cy="62" rx="13" ry="11" fill="${hlFill('delt-front-l')}" opacity="${hlOpacity('delt-front-l')}" transform="rotate(-12 60 62)"/>
  <ellipse id="delt-front-r" class="muscle-area ${hlClass('delt-front-r')}"
           cx="140" cy="62" rx="13" ry="11" fill="${hlFill('delt-front-r')}" opacity="${hlOpacity('delt-front-r')}" transform="rotate(12 140 62)"/>

  <!-- 肩部 - 三角肌中束 -->
  <ellipse id="delt-side-l" class="muscle-area ${hlClass('delt-side-l')}"
           cx="54" cy="72" rx="8" ry="12" fill="${hlFill('delt-side-l')}" opacity="${hlOpacity('delt-side-l')}" transform="rotate(-5 54 72)"/>
  <ellipse id="delt-side-r" class="muscle-area ${hlClass('delt-side-r')}"
           cx="146" cy="72" rx="8" ry="12" fill="${hlFill('delt-side-r')}" opacity="${hlOpacity('delt-side-r')}" transform="rotate(5 146 72)"/>

  <!-- 腹直肌 - 上腹 -->
  <path id="abs-upper" class="muscle-area ${hlClass('abs-upper')}"
        d="M86 98 Q100 95 114 98 Q112 108 110 115 Q100 118 90 115 Q88 108 86 98Z"
        fill="${hlFill('abs-upper')}" opacity="${hlOpacity('abs-upper')}"/>

  <!-- 腹直肌 - 下腹 -->
  <path id="abs-lower" class="muscle-area ${hlClass('abs-lower')}"
        d="M90 115 Q100 118 110 115 Q112 125 110 132 Q100 135 90 132 Q88 125 90 115Z"
        fill="${hlFill('abs-lower')}" opacity="${hlOpacity('abs-lower')}"/>

  <!-- 腹斜肌 -->
  <path id="oblique-l" class="muscle-area ${hlClass('oblique-l')}"
        d="M72 95 Q78 92 86 98 Q88 108 90 115 Q85 118 78 120 Q72 115 70 105 Q70 100 72 95Z"
        fill="${hlFill('oblique-l')}" opacity="${hlOpacity('oblique-l')}"/>
  <path id="oblique-r" class="muscle-area ${hlClass('oblique-r')}"
        d="M128 95 Q122 92 114 98 Q112 108 110 115 Q115 118 122 120 Q128 115 130 105 Q130 100 128 95Z"
        fill="${hlFill('oblique-r')}" opacity="${hlOpacity('oblique-r')}"/>

  <!-- 腹肌线条 -->
  <line x1="100" y1="98" x2="100" y2="135" stroke="#2D2456" stroke-width="0.8" opacity="0.35"/>
  <line x1="90" y1="106" x2="110" y2="106" stroke="#2D2456" stroke-width="0.5" opacity="0.25"/>
  <line x1="89" y1="115" x2="111" y2="115" stroke="#2D2456" stroke-width="0.5" opacity="0.25"/>
  <line x1="90" y1="124" x2="110" y2="124" stroke="#2D2456" stroke-width="0.5" opacity="0.25"/>

  <!-- 臀部 -->
  <path d="M76 135 Q78 130 100 128 Q122 130 124 135 Q128 148 124 155 Q112 162 100 162 Q88 162 76 155 Q72 148 76 135Z" class="body-base"/>

  <!-- === 左臂 === -->
  <!-- 上臂 -->
  <path d="M55 68 Q45 80 40 100 Q37 115 36 130 Q34 140 38 145"
        stroke="url(#bodyGrad)" stroke-width="15" fill="none" stroke-linecap="round"/>
  <!-- 肱二头肌 -->
  <ellipse id="bicep-l" class="muscle-area ${hlClass('bicep-l')}"
           cx="43" cy="92" rx="9" ry="14" fill="${hlFill('bicep-l')}" opacity="${hlOpacity('bicep-l')}" transform="rotate(-8 43 92)"/>
  <!-- 肱三头肌 -->
  <ellipse id="tricep-l" class="muscle-area ${hlClass('tricep-l')}"
           cx="49" cy="100" rx="7" ry="12" fill="${hlFill('tricep-l')}" opacity="${hlOpacity('tricep-l')}" transform="rotate(-8 49 100)"/>
  <!-- 前臂 -->
  <path d="M38 145 Q36 158 38 172 Q40 182 42 190"
        stroke="url(#bodyGrad)" stroke-width="11" fill="none" stroke-linecap="round"/>
  <!-- 手 -->
  <ellipse cx="42" cy="195" rx="6" ry="9" fill="#7B6CAA"/>

  <!-- === 右臂 === -->
  <path d="M145 68 Q155 80 160 100 Q163 115 164 130 Q166 140 162 145"
        stroke="url(#bodyGrad)" stroke-width="15" fill="none" stroke-linecap="round"/>
  <ellipse id="bicep-r" class="muscle-area ${hlClass('bicep-r')}"
           cx="157" cy="92" rx="9" ry="14" fill="${hlFill('bicep-r')}" opacity="${hlOpacity('bicep-r')}" transform="rotate(8 157 92)"/>
  <ellipse id="tricep-r" class="muscle-area ${hlClass('tricep-r')}"
           cx="151" cy="100" rx="7" ry="12" fill="${hlFill('tricep-r')}" opacity="${hlOpacity('tricep-r')}" transform="rotate(8 151 100)"/>
  <path d="M162 145 Q164 158 162 172 Q160 182 158 190"
        stroke="url(#bodyGrad)" stroke-width="11" fill="none" stroke-linecap="round"/>
  <ellipse cx="158" cy="195" rx="6" ry="9" fill="#7B6CAA"/>

  <!-- === 左腿 === -->
  <!-- 大腿 -->
  <path d="M82 158 Q78 180 76 205 Q75 225 78 245 Q80 258 82 265"
        stroke="url(#bodyGrad)" stroke-width="19" fill="none" stroke-linecap="round"/>
  <!-- 股四头肌 -->
  <ellipse id="quad-l" class="muscle-area ${hlClass('quad-l')}"
           cx="82" cy="195" rx="13" ry="20" fill="${hlFill('quad-l')}" opacity="${hlOpacity('quad-l')}"/>
  <!-- 腘绳肌 -->
  <ellipse id="hamstring-l" class="muscle-area ${hlClass('hamstring-l')}"
           cx="82" cy="215" rx="10" ry="15" fill="${hlFill('hamstring-l')}" opacity="${hlOpacity('hamstring-l')}"/>
  <!-- 小腿 -->
  <path d="M82 265 Q80 278 78 290 Q76 298 78 305"
        stroke="url(#bodyGrad)" stroke-width="13" fill="none" stroke-linecap="round"/>
  <!-- 腓肠肌 -->
  <ellipse id="calf-l" class="muscle-area ${hlClass('calf-l')}"
           cx="80" cy="282" rx="8" ry="12" fill="${hlFill('calf-l')}" opacity="${hlOpacity('calf-l')}"/>
  <!-- 脚 -->
  <ellipse cx="78" cy="308" rx="10" ry="6" fill="#7B6CAA"/>

  <!-- === 右腿 === -->
  <path d="M118 158 Q122 180 124 205 Q125 225 122 245 Q120 258 118 265"
        stroke="url(#bodyGrad)" stroke-width="19" fill="none" stroke-linecap="round"/>
  <ellipse id="quad-r" class="muscle-area ${hlClass('quad-r')}"
           cx="118" cy="195" rx="13" ry="20" fill="${hlFill('quad-r')}" opacity="${hlOpacity('quad-r')}"/>
  <ellipse id="hamstring-r" class="muscle-area ${hlClass('hamstring-r')}"
           cx="118" cy="215" rx="10" ry="15" fill="${hlFill('hamstring-r')}" opacity="${hlOpacity('hamstring-r')}"/>
  <path d="M118 265 Q120 278 122 290 Q124 298 122 305"
        stroke="url(#bodyGrad)" stroke-width="13" fill="none" stroke-linecap="round"/>
  <ellipse id="calf-r" class="muscle-area ${hlClass('calf-r')}"
           cx="120" cy="282" rx="8" ry="12" fill="${hlFill('calf-r')}" opacity="${hlOpacity('calf-r')}"/>
  <ellipse cx="122" cy="308" rx="10" ry="6" fill="#7B6CAA"/>

  <!-- 标注 -->
  <text x="100" y="14" text-anchor="middle" fill="#4ECDC4" font-size="10" font-weight="600">${this.highlightCategory || '全身'}</text>
  <text x="100" y="318" text-anchor="middle" fill="#4ECDC4" font-size="9" opacity="0.6">${this.highlightMuscle || ''}</text>
</svg>`;
  }
}

// 导出
window.BodyMap = BodyMap;
