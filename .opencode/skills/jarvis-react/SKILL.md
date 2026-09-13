---
name: jarvis-react
description: React component development with hooks, state management, Vite, Tailwind, and modern patterns.
license: MIT
metadata:
  domain: engineering
  complexity: medium
---

# React Development

## What I do

- React 19+ component development with hooks
- Vite build configuration and optimization
- Tailwind CSS 4 styling and responsive design
- Zustand state management
- React Router 7 navigation
- TypeScript strict mode patterns

## When to use me

Use this skill when working with React components, hooks, state management, Vite config, or Tailwind styling.

## Patterns

### Component Structure
```tsx
// Functional component with hooks
export function ComponentName({ prop1, prop2 }: Props) {
  const [state, setState] = useState(initialValue);
  const derived = useMemo(() => compute(state), [state]);
  
  useEffect(() => {
    // side effect
    return () => cleanup();
  }, [dependency]);
  
  return <div className="tailwind-classes">...</div>;
}
```

### State Management (Zustand)
```ts
const useStore = create<State>()((set, get) => ({
  data: null,
  loading: false,
  fetchData: async () => {
    set({ loading: true });
    const data = await api.getData();
    set({ data, loading: false });
  },
}));
```

### Lazy Loading
```tsx
const HeavyComponent = lazy(() => import('./HeavyComponent'));

<Suspense fallback={<Loading />}>
  <HeavyComponent />
</Suspense>
```

## Anti-patterns

- Don't use `any` type — use proper TypeScript types
- Don't mutate state directly — use setters
- Don't put side effects in render — use useEffect
- Don't forget cleanup in useEffect

---
*Source: Extracted from wshobson frontend-developer, application-performance agents*
