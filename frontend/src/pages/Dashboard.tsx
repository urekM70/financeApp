import { useState, useMemo, FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, ReferenceLine
} from 'recharts';
import { Wallet, TrendingUp, TrendingDown, DollarSign, Activity, ArrowRight, LucideProps } from 'lucide-react';
import { transactionApi } from '../services/api';
import type { Transaction } from '../types';
import { cn } from '../lib/utils';
import { useCurrencyFormatter } from '../hooks/useCurrencyFormatter';
import { useTranslation } from 'react-i18next';

type TimeRange = '30_days' | '6_months' | 'year';

/**
 * The main dashboard page for the application.
 * It displays an overview of financial statistics, charts, and recent transactions.
 */
export function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const formatCurrency = useCurrencyFormatter();
  const [timeRange, setTimeRange] = useState<TimeRange>('30_days');
  
  // Fetch transactions using React Query
  const { data: transactions, isLoading } = useQuery<Transaction[]>({
    queryKey: ['transactions'],
    queryFn: () => transactionApi.getTransactions(),
  });

  // Memoized calculation for financial statistics based on the selected time range
  const stats = useMemo(() => {
    if (!transactions) return null;

    const now = new Date();
    const currentPeriodStart = new Date(now);
    const previousPeriodStart = new Date();
    const previousPeriodEnd = new Date();

    // Determine the date ranges for the current and previous periods
    switch (timeRange) {
      case '30_days':
        currentPeriodStart.setDate(now.getDate() - 30);
        previousPeriodEnd.setDate(currentPeriodStart.getDate());
        previousPeriodStart.setDate(previousPeriodEnd.getDate() - 30);
        break;
      case '6_months':
        currentPeriodStart.setMonth(now.getMonth() - 6);
        previousPeriodEnd.setMonth(currentPeriodStart.getMonth());
        previousPeriodStart.setMonth(previousPeriodEnd.getMonth() - 6);
        break;
      case 'year':
        currentPeriodStart.setFullYear(now.getFullYear() - 1);
        previousPeriodEnd.setFullYear(currentPeriodStart.getFullYear());
        previousPeriodStart.setFullYear(previousPeriodEnd.getFullYear() - 1);
        break;
    }

    // Helper function to calculate income and expenses for a given period
    const calculatePeriodStats = (start: Date, end: Date) => {
      const periodTransactions = transactions.filter(t => {
        const d = new Date(t.date);
        return d >= start && d < end;
      });

      return periodTransactions.reduce((acc, t) => {
        if (t.type === 'income') acc.income += t.amount;
        else acc.expense += t.amount;
        return acc;
      }, { income: 0, expense: 0 });
    };

    const currentPeriod = calculatePeriodStats(currentPeriodStart, now);
    const previousPeriod = calculatePeriodStats(previousPeriodStart, previousPeriodEnd);

    // Helper function to calculate the percentage trend between two values
    const calculateTrend = (current: number, previous: number) => {
      if (previous === 0) return current === 0 ? 0 : 100;
      return ((current - previous) / Math.abs(previous)) * 100;
    };

    const incomeTrend = calculateTrend(currentPeriod.income, previousPeriod.income);
    const expenseTrend = calculateTrend(Math.abs(currentPeriod.expense), Math.abs(previousPeriod.expense));
    const netTrend = calculateTrend(currentPeriod.income + currentPeriod.expense, previousPeriod.income + previousPeriod.expense);

    return {
      income: currentPeriod.income,
      expense: currentPeriod.expense,
      net: currentPeriod.income + currentPeriod.expense,
      trends: { income: incomeTrend, expense: expenseTrend, net: netTrend },
      currentStart: currentPeriodStart,
    };
  }, [transactions, timeRange]);

  // Sort and slice transactions to get the most recent ones
  const recentTransactions = useMemo(() => {
    return (transactions || [])
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, 5);
  }, [transactions]);

  // Memoized data processing for the cash flow bar chart
  const chartData = useMemo(() => {
    if (!transactions || !stats) return [];

    const filtered = transactions.filter(t => new Date(t.date) >= stats.currentStart);
    const aggregated = filtered.reduce((acc, t) => {
      const dateKey = t.date.split('T')[0];
      if (!acc[dateKey]) acc[dateKey] = { date: dateKey, income: 0, expense: 0 };
      if (t.type === 'income') acc[dateKey].income += t.amount;
      else acc[dateKey].expense -= t.amount; // Store expenses as positive numbers for chart
      return acc;
    }, {} as Record<string, { date: string; income: number; expense: number }>);

    return Object.values(aggregated)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .map(item => ({
        ...item,
        displayDate: new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      }));
  }, [transactions, stats]);

  // Memoized data processing for the expenses by category pie chart
  const categoryData = useMemo(() => {
    if (!transactions || !stats) return [];

    return Object.entries(
      transactions
        .filter(t => t.type === 'expense' && new Date(t.date) >= stats.currentStart)
        .reduce((acc, t) => {
          acc[t.category] = (acc[t.category] || 0) + Math.abs(t.amount);
          return acc;
        }, {} as Record<string, number>)
    ).map(([name, value]) => ({ name, value }));
  }, [transactions, stats]);

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6366F1'];

  const trendLabel = timeRange === '30_days' ? t('FromLast30Days') 
    : timeRange === '6_months' ? t('FromPrevious6Months') 
    : t('FromPreviousYear');

  // Display a loading spinner while data is being fetched
  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 dark:text-white tracking-tight">{t('FinancialOverview')}</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">{t('TrackYourIncome')}</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => navigate('/upload')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            {t('Upload transactions')}
          </button>
        </div>
      </div>
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <SummaryCard 
          title={t('TotalIncome')} 
          amount={formatCurrency(stats?.income || 0)} 
          icon={TrendingUp} 
          trend={`${(stats?.trends.income || 0).toFixed(1)}%`} 
          trendUp={(stats?.trends.income || 0) >= 0}
          trendLabel={trendLabel}
          gradient="from-green-500 to-emerald-600"
          shadowColor="shadow-green-500/20"
        />
        <SummaryCard 
          title={t('TotalExpenses')} 
          amount={formatCurrency(Math.abs(stats?.expense || 0))} 
          icon={TrendingDown} 
          trend={`${(stats?.trends.expense || 0).toFixed(1)}%`} 
          trendUp={(stats?.trends.expense || 0) <= 0}
          trendLabel={trendLabel}
          gradient="from-red-500 to-pink-600"
          shadowColor="shadow-red-500/20"
        />
        <SummaryCard 
          title={t('NetBalance')} 
          amount={formatCurrency(stats?.net || 0)} 
          icon={Wallet} 
          trend={`${(stats?.trends.net || 0).toFixed(1)}%`} 
          trendUp={(stats?.trends.net || 0) >= 0}
          trendLabel={trendLabel}
          gradient="from-blue-500 to-indigo-600"
          shadowColor="shadow-blue-500/20"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Cash Flow Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 p-6 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              {t('CashFlow')}
            </h2>
            <select 
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="text-sm border-none bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-200 rounded-lg px-3 py-1 focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="30_days">{t('Last30Days')}</option>
              <option value="6_months">{t('Last6Months')}</option>
              <option value="year">{t('LastYear')}</option>
            </select>
          </div>
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(226, 232, 240, 0.5)" />
                <XAxis dataKey="displayDate" axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#94A3B8', fontSize: 12}} tickFormatter={(value) => formatCurrency(value)} />
                <Tooltip 
                  cursor={{ fill: 'rgba(241, 245, 249, 0.5)' }}
                  contentStyle={{ backgroundColor: 'white', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '8px 12px' }}
                  formatter={(value: number, name: string) => [formatCurrency(Math.abs(value)), name.charAt(0).toUpperCase() + name.slice(1)]}
                  labelStyle={{ color: '#64748B', marginBottom: '4px', fontWeight: '500' }}
                />
                <ReferenceLine y={0} stroke="#E2E8F0" />
                <Bar dataKey="income" name={t('Income')} fill="#10B981" radius={[4, 4, 0, 0]} maxBarSize={40} />
                <Bar dataKey="expense" name={t('Expense')} fill="#EF4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Expenses by Category Chart */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-orange-500" />
            {t('ExpensesByCategory')}
          </h2>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={categoryData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={3} dataKey="value" nameKey="name">
                  {categoryData.map((_, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-x-4 gap-y-2">
            {categoryData.map((entry, index) => (
              <div key={entry.name} className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                <span className="text-slate-600 dark:text-slate-400">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Transactions Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white">{t('RecentTransactions')}</h2>
          <button onClick={() => navigate('/transactions')} className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1">
            {t('ViewAll')} <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 dark:divide-slate-800">
            <tbody className="bg-white dark:bg-slate-900 divide-y divide-slate-100 dark:divide-slate-800">
              {recentTransactions.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-6 sm:px-6 sm:py-8 text-center text-slate-500 dark:text-slate-400">
                    {t('NoTransactionsYet')}
                  </td>
                </tr>
              ) : (
                recentTransactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-4 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400 w-32">
                      {new Date(transaction.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 sm:px-6 sm:py-4 text-sm font-medium text-slate-900 dark:text-white">
                      {transaction.description}
                    </td>
                    <td className="px-4 py-3 sm:px-6 sm:py-4 text-sm">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
                        {transaction.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-sm font-medium text-right">
                      <span className={transaction.type === 'expense' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}>
                        {transaction.type === 'expense' ? '-' : ''}{formatCurrency(Math.abs(transaction.amount))}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/**
 * A reusable component for displaying a summary card on the dashboard.
 */
interface SummaryCardProps {
  title: string;
  amount: string;
  icon: React.ComponentType<LucideProps>;
  trend: string;
  trendUp: boolean;
  trendLabel: string;
  gradient: string;
  shadowColor: string;
}

const SummaryCard: FC<SummaryCardProps> = ({ title, amount, icon: Icon, trend, trendUp, trendLabel, gradient, shadowColor }) => {
  return (
    <div className={cn("bg-white dark:bg-slate-900 p-6 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 relative overflow-hidden group hover:shadow-lg transition-all", shadowColor)}>
      <div className="relative z-10">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
            <h3 className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">{amount}</h3>
          </div>
          <div className={cn("p-3 rounded-xl bg-gradient-to-br shadow-lg text-white transform group-hover:scale-110 transition-transform", gradient)}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <div className="mt-4 flex items-center text-sm">
          <span className={cn("font-medium flex items-center gap-1", trendUp ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400")}>
            {trendUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {trend}
          </span>
          <span className="text-slate-400 dark:text-slate-500 ml-2">{trendLabel}</span>
        </div>
      </div>
    </div>
  );
};
