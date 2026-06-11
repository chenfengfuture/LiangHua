import React from 'react';
import { Button, Typography } from 'antd';
import { useTheme } from '@/themes';

const { Text } = Typography;

interface Props {
  children: React.ReactNode;
  /** 显示在错误边界的标题，方便定位是哪个区块崩溃 */
  name?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React 错误边界组件
 *
 * 包裹子组件树，当内部任何组件抛出 JS 运行时错误时，
 * 捕获并展示降级 UI，而不是让整个页面白屏。
 *
 * 用法：
 *   <ErrorBoundary name="Dashboard">
 *     <Dashboard />
 *   </ErrorBoundary>
 */
class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[ErrorBoundary${this.props.name ? `:${this.props.name}` : ''}]`, error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return <ErrorFallback name={this.props.name} error={this.state.error} onRetry={this.handleRetry} />;
    }
    return this.props.children;
  }
}

/** 降级 UI（函数组件，可使用 hooks） */
const ErrorFallback: React.FC<{ name?: string; error: Error | null; onRetry: () => void }> = ({ name, error, onRetry }) => {
  const { colors } = useTheme();
  return (
    <div style={{
      padding: 24,
      textAlign: 'center',
      background: colors.bgCard,
      border: `1px solid ${colors.borderColor}`,
      borderRadius: 12,
      minHeight: 120,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
    }}>
      <Text style={{ color: colors.textPrimary, fontSize: 14, fontWeight: 600 }}>
        {name ? `${name} ` : ''}渲染异常
      </Text>
      <Text style={{ color: colors.textTertiary, fontSize: 12 }}>
        {error?.message || '未知错误'}
      </Text>
      <Button size="small" type="primary" onClick={onRetry}>
        重试
      </Button>
    </div>
  );
};

export default ErrorBoundary;
