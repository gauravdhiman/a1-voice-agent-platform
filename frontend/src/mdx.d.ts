declare module "*.mdx" {
  export const metadata: {
    title: string;
    description: string;
    date: string;
    slug: string;
  };
  const MDXComponent: (props: Record<string, unknown>) => JSX.Element;
  export default MDXComponent;
}
