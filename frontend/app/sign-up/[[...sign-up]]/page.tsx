import { SignUp } from '@clerk/nextjs'

export default function Page() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="w-full max-w-md">
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-gray-900/50 border border-gray-800",
              headerTitle: "hidden",
              headerSubtitle: "hidden",
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
