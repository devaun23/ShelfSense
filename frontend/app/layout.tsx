import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import { ClerkProvider, ClerkLoading, ClerkLoaded } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import "./globals.css";
import { UserProvider } from "@/contexts/UserContext";
import { ExamProvider } from "@/contexts/ExamContext";
import PaymentStatusBanner from "@/components/PaymentStatusBanner";
import ErrorBoundary from "@/components/ErrorBoundary";
import ClerkLoadingSpinner from "@/components/ClerkLoadingSpinner";

const inter = Inter({
  subsets: ["latin"],
  display: 'swap',
  variable: '--font-inter',
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-serif',
});

export const metadata: Metadata = {
  title: "ShelfPass",
  description: "Adaptive learning platform for USMLE Step 2 CK",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: '#4169E1',
          colorBackground: '#000000',
          colorInputBackground: '#0a0a0a',
          colorInputText: '#ffffff',
        },
        elements: {
          formButtonPrimary: 'bg-[#4169E1] hover:bg-[#5B7FE8]',
          card: 'bg-black border border-gray-800',
          headerTitle: 'text-white',
          headerSubtitle: 'text-gray-400',
          socialButtonsBlockButton: 'bg-gray-900 border-gray-700 text-white hover:bg-gray-800',
          formFieldLabel: 'text-gray-400',
          formFieldInput: 'bg-gray-950 border-gray-800 text-white',
          footerActionLink: 'text-[#4169E1] hover:text-[#5B7FE8]',
        },
      }}
    >
      <html lang="en">
        <body className={`${inter.variable} ${sourceSerif.variable} ${inter.className} antialiased`}>
          <ClerkLoading>
            <ClerkLoadingSpinner />
          </ClerkLoading>
          <ClerkLoaded>
            <ErrorBoundary>
              <UserProvider>
                <ExamProvider>
                  <PaymentStatusBanner />
                  {children}
                </ExamProvider>
              </UserProvider>
            </ErrorBoundary>
          </ClerkLoaded>
        </body>
      </html>
    </ClerkProvider>
  );
}
