# 📂 项目完整结构

## 文件树

```
elderly-care-mvp/
│
├── 📄 package.json                 # NPM 依赖和脚本配置
├── 📄 tsconfig.json                # TypeScript 配置
├── 📄 next.config.js               # Next.js 配置
├── 📄 tailwind.config.js           # Tailwind CSS 配置
├── 📄 postcss.config.js            # PostCSS 配置（用于 Tailwind）
├── 📄 .gitignore                   # Git 忽略文件
│
├── 📄 README.md                    # 项目说明文档
├── 📄 QUICK_START.md               # 快速启动指南
├── 📄 PROJECT_STRUCTURE.md         # 本文件（项目结构说明）
│
├── 📁 src/                         # 源代码目录
│   │
│   ├── 📁 app/                     # Next.js App Router
│   │   ├── 📄 layout.tsx           # 根页面布局（HTML 骨架）
│   │   ├── 📄 page.tsx             # 首页组件入口
│   │   └── 📄 globals.css          # 全局样式和 Tailwind 指令
│   │
│   ├── 📁 components/              # React 组件目录
│   │   └── 📄 StatusDashboard.tsx  # 状态仪表板主组件
│   │       - 展示老人状态
│   │       - 管理用户交互
│   │       - 处理按钮点击
│   │
│   └── 📁 data/                    # Mock 数据目录
│       └── 📄 mockData.ts          # 老人状态的 Mock 数据
│           - 定义数据结构（ElderlyData）
│           - 提供示例数据
│
└── 📁 .next/                       # Next.js 构建输出（自动生成，无需提交）
    └── （自动生成文件）

```

## 文件说明

### 根目录配置文件

| 文件 | 说明 |
|------|------|
| `package.json` | 定义项目依赖、版本和 npm 脚本 |
| `tsconfig.json` | TypeScript 编译器配置 |
| `next.config.js` | Next.js 框架配置 |
| `tailwind.config.js` | Tailwind CSS 主题和扩展配置 |
| `postcss.config.js` | PostCSS 插件配置（用于处理 CSS） |
| `.gitignore` | Git 忽略的文件列表 |

### 文档文件

| 文件 | 用途 |
|------|------|
| `README.md` | 完整的项目说明和使用指南 |
| `QUICK_START.md` | 快速启动步骤和常见问题 |
| `PROJECT_STRUCTURE.md` | 本文件，项目结构详解 |

### 源代码目录 (`src/`)

#### `src/app/` - Next.js App Router 目录

**`layout.tsx`** - 根布局文件
```typescript
// 定义 HTML 的 <head> 和 <body>
// 所有页面的上层布局
export const metadata = {
  title: '老人状态监护',
  description: '家属快速判断老人是否正常',
  viewport: { /* ... */ }
};

export default function RootLayout({ children }) {
  return (
    <html>
      <head>{/* 元标签 */}</head>
      <body>{children}</body>
    </html>
  );
}
```

**`page.tsx`** - 首页组件
```typescript
// 页面入口，渲染 StatusDashboard 组件
export default function Home() {
  return <StatusDashboard />;
}
```

**`globals.css`** - 全局样式
```css
/* Tailwind CSS 指令 */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 自定义全局样式 */
body {
  font-family: system-ui;
  background-color: #f9fafb;
}
```

#### `src/components/` - React 组件目录

**`StatusDashboard.tsx`** - 主要业务组件
```typescript
'use client';  // 客户端组件标记

import { mockData } from '@/data/mockData';

export default function StatusDashboard() {
  // 状态管理：确认按钮的反馈
  const [isConfirmed, setIsConfirmed] = useState(false);

  // 处理确认操作
  const handleConfirm = () => {
    console.log('已确认正常 - 时间:', new Date().toLocaleString());
    setIsConfirmed(true);
    setTimeout(() => setIsConfirmed(false), 2000);
  };

  return (
    <div>
      {/* 主状态卡片 */}
      <div className="text-5xl font-bold">
        {mockData.statusLabel}
      </div>

      {/* 当前状态卡片 */}
      <div>{mockData.currentState}</div>

      {/* 行为记录列表 */}
      <div>
        {mockData.recentEvents.map(...)}
      </div>

      {/* 异常提醒（如果存在） */}
      {mockData.alert?.exists && (
        <div>{/* 提醒内容 */}</div>
      )}

      {/* 操作按钮 */}
      <button onClick={handleConfirm}>
        {isConfirmed ? '✓ 已确认正常' : '确认正常'}
      </button>
    </div>
  );
}
```

#### `src/data/` - Mock 数据目录

**`mockData.ts`** - 数据定义和示例
```typescript
export interface ElderlyData {
  name: string;                        // 老人名字
  status: 'normal' | 'attention' | 'high_risk';  // 状态
  statusLabel: string;                 // 状态标签
  statusColor: string;                 // 状态颜色类
  currentState: string;                // 当前活动
  currentLocation: string;             // 当前位置
  recentEvents: Array<{               // 最近行为
    time: string;
    activity: string;
  }>;
  alert: {                            // 异常提醒
    exists: boolean;
    title: string;
    description: string;
    duration: string;
    suggestion: string;
  } | null;
}

export const mockData: ElderlyData = {
  // 实际数据内容
};
```

---

## 数据流向

```
page.tsx (首页入口)
    ↓
StatusDashboard.tsx (主组件)
    ↓
mockData.ts (读取 Mock 数据)
    ↓
render (在浏览器中显示)
    ↓
用户交互（点击按钮）
    ↓
setState (更新状态)
    ↓
console.log (输出日志)
```

---

## 关键代码位置

### 如果你想修改...

| 修改内容 | 文件位置 |
|---------|--------|
| 老人名字 | `src/data/mockData.ts` - `name` 字段 |
| 显示的状态 | `src/data/mockData.ts` - `status` 字段 |
| 当前位置 | `src/data/mockData.ts` - `currentState` 字段 |
| 行为记录 | `src/data/mockData.ts` - `recentEvents` 数组 |
| 异常提醒 | `src/data/mockData.ts` - `alert` 对象 |
| 页面标题 | `src/app/layout.tsx` - `metadata.title` |
| 按钮颜色 | `src/components/StatusDashboard.tsx` - `className` |
| 字体大小 | `tailwind.config.js` - `fontSize` 或组件中的 `className` |
| 页面背景颜色 | `src/app/globals.css` 或 `tailwind.config.js` |

---

## 环境路径映射

项目中使用了路径别名，方便导入：

| 别名 | 实际路径 |
|------|---------|
| `@/*` | `src/*` |

所以：
- `import StatusDashboard from '@/components/StatusDashboard'` 
- 等同于 `import StatusDashboard from 'src/components/StatusDashboard'`

---

## 构建输出

运行 `npm run build` 后会生成：

```
.next/
├── static/       # 静态文件（JavaScript、CSS）
├── server/       # 服务器端代码
└── ...           # 其他构建输出
```

这些文件在 `.gitignore` 中被忽略，不需要提交到版本控制。

---

## 依赖关系

```
package.json
    ├── react@18.3.1
    ├── react-dom@18.3.1
    ├── next@15.0.0
    │
    └── devDependencies
        ├── typescript
        ├── @types/react
        ├── @types/react-dom
        ├── @types/node
        ├── tailwindcss
        ├── postcss
        ├── autoprefixer
        └── @tailwindcss/forms
```

---

## 总结

- **配置文件**（根目录）：项目框架和工具配置
- **文档**（README、QUICK_START 等）：使用说明
- **源代码**（src/）：实际业务逻辑
  - `app/` - Next.js 页面和全局配置
  - `components/` - React 组件
  - `data/` - Mock 数据
- **自动生成**（.next/）：构建输出

所有关键代码都在 `src/` 目录中，通常只需要修改 `mockData.ts` 来改变页面内容。

👍 祝开发愉快！
