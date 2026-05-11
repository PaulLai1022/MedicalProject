import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { login } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { PasswordInput } from "@/components/form/PasswordInput";

const schema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [error, setError] = useState("");

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setError("");
    try {
      const resp = await login(data.email, data.password);
      setAuth(resp.accessToken, resp.user);
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: { message?: string } } } })
        ?.response?.data?.error?.message || "Login failed";
      setError(msg);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FAFAFA]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Sign In</h1>
          <p className="text-sm text-gray-500 mt-1">Clinical Note Structuring Tool</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
              <input
                {...register("email")}
                type="email"
                autoComplete="email"
                className="w-full h-11 border border-gray-200 rounded-xl px-4 text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"
              />
              {errors.email && <p className="text-red-500 text-xs mt-1.5">{errors.email.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
              <PasswordInput registration={register("password")} />
              {errors.password && <p className="text-red-500 text-xs mt-1.5">{errors.password.message}</p>}
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 bg-gray-900 text-white text-sm font-medium rounded-xl
                         hover:bg-gray-800 active:scale-[0.98] disabled:opacity-50 transition-all"
            >
              {isSubmitting ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>
        <p className="text-center text-sm text-gray-500 mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-blue-600 hover:text-blue-700 font-medium">Sign Up</Link>
        </p>
      </div>
    </div>
  );
}
