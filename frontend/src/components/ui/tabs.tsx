/**
 * Animated Tabs Component with URL Synchronization
 *
 * CURRENT PATTERN (Single Section per Page):
 * ---------------------------------------
 * Each page uses a single tab section with a `?tab=` query parameter:
 *
 *   const searchParams = useSearchParams();
 *   const [activeTab, setActiveTab] = useState('default');
 *
 *   useEffect(() => {
 *     const tabParam = searchParams.get('tab');
 *     if (tabParam) setActiveTab(tabParam);
 *   }, [searchParams]);
 *
 *   const handleTabChange = (value: string) => {
 *     setActiveTab(value);
 *     router.push(`/page?tab=${value}`, { scroll: false });
 *   };
 *
 *   <AnimatedTabs value={activeTab} onValueChange={handleTabChange}>
 *     <TabsTrigger value="tab1">Tab 1</TabsTrigger>
 *     <TabsTrigger value="tab2">Tab 2</TabsTrigger>
 *   </AnimatedTabs>
 *
 *
 * EXTENDING FOR MULTIPLE SECTIONS:
 * ---------------------------------------
 * If a page has multiple independent tab sections, use prefixed query parameters:
 *
 *   URL: /agents?view_tab=list&filter_tab=org&tools_tab=enabled
 *
 *   const [viewTab, setViewTab] = useTabState('view', 'list');
 *   const [filterTab, setFilterTab] = useTabState('filter', 'org');
 *   const [toolsTab, setToolsTab] = useTabState('tools', 'enabled');
 *
 *   Create a reusable hook (hooks/use-tab-state.ts):
 *
 *   export function useTabState(sectionId: string, defaultValue: string) {
 *     const searchParams = useSearchParams();
 *     const router = useRouter();
 *     const paramKey = `${sectionId}_tab`;
 *
 *     const [activeTab, setActiveTabState] = useState(() =>
 *       searchParams.get(paramKey) || defaultValue
 *     );
 *
 *     useEffect(() => {
 *       const tabParam = searchParams.get(paramKey);
 *       if (tabParam) setActiveTabState(tabParam);
 *     }, [searchParams, paramKey]);
 *
 *     const setActiveTab = useCallback((value: string) => {
 *       setActiveTabState(value);
 *       const params = new URLSearchParams(searchParams.toString());
 *       params.set(paramKey, value);
 *       router.push(`${window.location.pathname}?${params}`, { scroll: false });
 *     }, [router, searchParams, paramKey]);
 *
 *     return [activeTab, setActiveTab];
 *   }
 *
 * Migration from current to multi-section approach is minimal - just replace
 * useState/useEffect pattern with the useTabState hook.
 */

"use client"

import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

const TabsContext = React.createContext<{ activeTab?: string }>({})

const Tabs = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Root>
>(({ className, value, onValueChange, defaultValue, ...props }, ref) => {
  const [internalValue, setInternalValue] = React.useState(value || defaultValue)

  const handleValueChange = (newValue: string) => {
    setInternalValue(newValue)
    onValueChange?.(newValue)
  }

  React.useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value)
    }
  }, [value])

  return (
    <TabsContext.Provider value={{ activeTab: value !== undefined ? value : internalValue }}>
      <TabsPrimitive.Root
        ref={ref}
        value={value}
        defaultValue={defaultValue}
        onValueChange={handleValueChange}
        className={className}
        {...props}
      />
    </TabsContext.Provider>
  )
})
Tabs.displayName = TabsPrimitive.Root.displayName

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-auto items-center justify-start bg-background rounded-none border-b border-border p-0 gap-0 w-full",
      className
    )}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, value, children, ...props }, ref) => {
  const { activeTab } = React.useContext(TabsContext)
  const isActive = activeTab === value

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      value={value}
      className={cn(
        "relative bg-background dark:data-[state=active]:bg-background z-10 rounded-none border-0 data-[state=active]:shadow-none px-6 py-3 text-sm font-medium transition-all duration-200 whitespace-nowrap",
        "hover:text-foreground/80 data-[state=active]:text-foreground hover:bg-accent/50",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
      {...props}
    >
      {children}
      {isActive && (
        <motion.div
          layoutId="active-tab-underline"
          className="absolute bottom-0 left-0 h-[2px] w-full bg-primary z-20"
          transition={{ type: "spring", stiffness: 400, damping: 40 }}
        />
      )}
    </TabsPrimitive.Trigger>
  )
})
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

// Backward compatibility for AnimatedTabs
const AnimatedTabs = Tabs

export { Tabs, TabsList, TabsTrigger, TabsContent, AnimatedTabs }