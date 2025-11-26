import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      {/* ShelfSense branding */}
      <div className="text-center mb-8">
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
    </main>
  );
}
