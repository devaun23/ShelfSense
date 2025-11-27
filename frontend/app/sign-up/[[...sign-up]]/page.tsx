import { SignUp } from '@clerk/nextjs'

export default function Page() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="w-full max-w-md">
        {/* ShelfSense branding */}
        <div className="text-center mb-8">
          <h1
            className="text-6xl tracking-wide font-light mb-2 text-white"
            style={{ fontFamily: 'var(--font-cormorant)' }}
          >
            ShelfSense
          </h1>
          <p className="text-gray-400 text-sm">Create an account to start studying</p>
        </div>

        {/* Clerk Sign Up Component */}
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-gray-900/50 border border-gray-800",
              headerTitle: "text-white",
              headerSubtitle: "text-gray-400",
              socialButtonsBlockButton: "bg-gray-800 border-gray-700 hover:bg-gray-700 text-white",
              socialButtonsBlockButtonText: "text-white",
              formButtonPrimary: "bg-[#4169E1] hover:bg-[#3158D0] text-white",
              formFieldInput: "bg-black border-gray-700 text-white",
              formFieldLabel: "text-gray-300",
              footerActionLink: "text-[#4169E1] hover:text-[#3158D0]",
              identityPreviewText: "text-white",
              formFieldInputShowPasswordButton: "text-gray-400"
            }
          }}
        />
      </div>
    </div>
  )
}
