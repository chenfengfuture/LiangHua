import { createContext, useContext, useState, useMemo, ReactNode } from 'react';

type ThemeType = 'dark' | 'light';

interface ThemeColors {
  bgPrimary: string;
  bgSecondary: string;
  bgCard: string;
  borderColor: string;
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  accentBlue: string;
  accentBlue2: string;
  accentPurple1: string;
  accentPurple2: string;
  accentGreen: string;
  accentRed: string;
  hoverBg: string;
}

export const darkColors: ThemeColors = {
  bgPrimary: '#0D0D0E',
  bgSecondary: '#161618',
  bgCard: '#1E1E20',
  borderColor: '#2A2A2D',
  textPrimary: '#FFFFFF',
  textSecondary: '#A0A0A5',
  textTertiary: '#6B6B70',
  accentBlue: '#56A4FF',
  accentBlue2: '#546ACF',
  accentPurple1: '#514EBD',
  accentPurple2: '#ACA9CC',
  accentGreen: '#10B981',
  accentRed: '#EF4444',
  hoverBg: '#252528',
};

export const lightColors: ThemeColors = {
  bgPrimary: '#F8FAFC',
  bgSecondary: '#FFFFFF',
  bgCard: '#FFFFFF',
  borderColor: '#E2E8F0',
  textPrimary: '#1E293B',
  textSecondary: '#64748B',
  textTertiary: '#94A3B8',
  accentBlue: '#56A4FF',
  accentBlue2: '#546ACF',
  accentPurple1: '#514EBD',
  accentPurple2: '#ACA9CC',
  accentGreen: '#10B981',
  accentRed: '#EF4444',
  hoverBg: '#F1F5F9',
};

interface ThemeContextType {
  theme: ThemeType;
  colors: ThemeColors;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [theme, setTheme] = useState<ThemeType>('dark');
  const colors = useMemo(() => theme === 'dark' ? darkColors : lightColors, [theme]);

  const toggleTheme = useMemo(() => () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  }, []);

  const contextValue = useMemo(() => ({ theme, colors, toggleTheme }), [theme, colors, toggleTheme]);

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
