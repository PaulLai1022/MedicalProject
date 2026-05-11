import { useState } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";

interface PasswordInputProps {
  registration: UseFormRegisterReturn;
  placeholder?: string;
}

function EyeOpen() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeClosed() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
    </svg>
  );
}

export function PasswordInput({ registration, placeholder }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <input
        {...registration}
        type={visible ? "text" : "password"}
        placeholder={placeholder}
        className="w-full border rounded px-3 py-2 pr-10"
      />
      <button
        type="button"
        onClick={() => setVisible(!visible)}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700 p-1"
        tabIndex={-1}
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? <EyeClosed /> : <EyeOpen />}
      </button>
    </div>
  );
}
