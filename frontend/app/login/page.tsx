import { redirect } from 'next/navigation';

// Redirect old /login route to new Clerk sign-in page
export default function LoginPage() {
  redirect('/sign-in');
}
