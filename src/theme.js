/**
 * Shared Tailwind Configuration for VoteChain V3
 * ensures consistent branding, colors, and fonts across all pages.
 */
tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['Space Grotesk', 'sans-serif'],
                display: ['Space Grotesk', 'sans-serif']
            },
            colors: {
                // Neutral scales for UI structure
                black: '#050505',
                white: '#ffffff',
                subtle: '#888888',
                border: '#eaeaea',
                darkBorder: '#1a1a1a',

                // Semantic Colors
                accent: '#6366f1', // Indigo-500 (Primary Brand)
                success: '#22c55e', // Green-500 (Verified/Safe)
                error: '#ef4444',   // Red-500 (Danger/Failed)
                warning: '#f59e0b', // Amber-500 (Pending/Caution)

                // Extended Brand Palette (Indigo)
                brand: {
                    50: '#eef2ff',
                    100: '#e0e7ff',
                    500: '#6366f1',
                    600: '#4f46e5',
                    700: '#4338ca',
                    900: '#312e81',
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                }
            }
        }
    }
};
