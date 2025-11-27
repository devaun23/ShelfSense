import { SignUp } from '@clerk/nextjs';
import Link from 'next/link';
import ShelfSenseLogo from '@/components/icons/ShelfSenseLogo';

export default function SignUpPage() {
  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      {/* ShelfSense branding */}
      <div className="flex flex-col items-center mb-8">
        <ShelfSenseLogo size={48} animate={true} className="mb-4" />
        <h1
          className="text-5xl tracking-normal font-semibold text-white"
          style={{ fontFamily: 'var(--font-serif)' }}
        >
          ShelfSense
        </h1>
      </div>

      <SignUp
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-black border border-gray-800 shadow-xl',
          },
        }}
      />

      <p className="mt-6 text-sm text-gray-500 text-center max-w-sm">
        By signing up, you agree to our{' '}
        <Link href="/terms" className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors">
          Terms of Service
        </Link>{' '}
        and{' '}
        <Link href="/privacy" className="text-[#4169E1] hover:text-[#5B7FE8] transition-colors">
          Privacy Policy
        </Link>
      </p>
    </main>
  );
}
