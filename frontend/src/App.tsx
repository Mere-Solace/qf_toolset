import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import YieldCurve from "./pages/YieldCurve";
import OptionsPricer from "./pages/OptionsPricer";
import MacroIndicators from "./pages/MacroIndicators";
import AnalysisResults from "./pages/AnalysisResults";
import StockFinancials from "./pages/StockFinancials";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/yield-curve" element={<YieldCurve />} />
        <Route path="/options" element={<OptionsPricer />} />
        <Route path="/macro" element={<MacroIndicators />} />
        <Route path="/analysis" element={<AnalysisResults />} />
        <Route path="/financials" element={<StockFinancials />} />
      </Routes>
    </Layout>
  );
}

export default App;
