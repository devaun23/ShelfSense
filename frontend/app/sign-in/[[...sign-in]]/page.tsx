import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      {/* ShelfSense branding */}
      <div className="text-center mb-8">
        <h1
          className="text-5xl tracking-wide font-light text-white mb-3"
          style={{ fontFamily: 'var(--font-cormorant)' }}
        >
          ShelfSense
        </h1>
        <p className="text-gray-500 text-sm">
          Adaptive learning for Step 2 CK
        </p>
      </div>

      <SignIn
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-black border border-gray-800 shadow-xl',
          },
        }}
      />
    </main>
  );
}
