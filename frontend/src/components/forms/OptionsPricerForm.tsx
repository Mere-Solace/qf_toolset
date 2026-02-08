import { useState } from "react";

export type ModelType = "bs" | "binomial" | "mc";

export interface OptionFormValues {
  S: number;
  K: number;
  T: number;
  r: number;
  sigma: number;
  option_type: "call" | "put";
  model: ModelType;
  steps: number;
  simulations: number;
}

interface OptionsPricerFormProps {
  onSubmit: (values: OptionFormValues) => void;
  isLoading?: boolean;
}

const defaultValues: OptionFormValues = {
  S: 100,
  K: 100,
  T: 0.25,
  r: 0.05,
  sigma: 0.2,
  option_type: "call",
  model: "bs",
  steps: 100,
  simulations: 100000,
};

const inputClass =
  "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent";

const labelClass = "block text-xs font-medium text-slate-400 mb-1";

export default function OptionsPricerForm({
  onSubmit,
  isLoading = false,
}: OptionsPricerFormProps) {
  const [values, setValues] = useState<OptionFormValues>(defaultValues);

  const set = <K extends keyof OptionFormValues>(
    key: K,
    val: OptionFormValues[K]
  ) => setValues((prev) => ({ ...prev, [key]: val }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(values);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClass}>Spot Price (S)</label>
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={values.S}
            onChange={(e) => set("S", parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className={labelClass}>Strike Price (K)</label>
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={values.K}
            onChange={(e) => set("K", parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className={labelClass}>Time to Expiry (T, years)</label>
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={values.T}
            onChange={(e) => set("T", parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className={labelClass}>Risk-Free Rate (r)</label>
          <input
            type="number"
            step="0.001"
            className={inputClass}
            value={values.r}
            onChange={(e) => set("r", parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className={labelClass}>Volatility (sigma)</label>
          <input
            type="number"
            step="0.01"
            className={inputClass}
            value={values.sigma}
            onChange={(e) => set("sigma", parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className={labelClass}>Option Type</label>
          <select
            className={inputClass}
            value={values.option_type}
            onChange={(e) =>
              set("option_type", e.target.value as "call" | "put")
            }
          >
            <option value="call">Call</option>
            <option value="put">Put</option>
          </select>
        </div>
      </div>

      <div>
        <label className={labelClass}>Pricing Model</label>
        <div className="flex gap-2">
          {(
            [
              ["bs", "Black-Scholes"],
              ["binomial", "Binomial Tree"],
              ["mc", "Monte Carlo"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => set("model", value)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                values.model === value
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {values.model === "binomial" && (
        <div>
          <label className={labelClass}>Steps</label>
          <input
            type="number"
            className={inputClass}
            value={values.steps}
            onChange={(e) => set("steps", parseInt(e.target.value) || 100)}
          />
        </div>
      )}

      {values.model === "mc" && (
        <div>
          <label className={labelClass}>Simulations</label>
          <input
            type="number"
            className={inputClass}
            value={values.simulations}
            onChange={(e) =>
              set("simulations", parseInt(e.target.value) || 100000)
            }
          />
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
      >
        {isLoading ? "Pricing..." : "Calculate Price"}
      </button>
    </form>
  );
}
