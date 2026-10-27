import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthGuard } from './components/auth/AuthGuard'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { AlertDetailPage } from './pages/AlertDetailPage'
import { AlertsListPage } from './pages/AlertsListPage'
import { BacktestPage } from './pages/BacktestPage'
import { HealthPage } from './pages/HealthPage'
import { DataSourcesPage, AlertingRulesPage, SlackConfigPage } from './pages/AdminPage'
import { PublishersPage } from './pages/PublishersPage'
import { PublisherDetailPage } from './pages/PublisherDetailPage'
import { OperationalDocsPage, TechnicalDocsPage } from './pages/DocsPage'

function NotFoundPage() {
  return (
    <div className="py-20 text-center">
      <h1 className="text-4xl font-bold text-gray-900">404</h1>
      <p className="mt-2 text-gray-500">Page not found.</p>
      <Link to="/dashboard" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
        Go to Dashboard
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <AuthGuard>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/alerts" element={<AlertsListPage />} />
          <Route path="/alerts/:alertId" element={<AlertDetailPage />} />
          <Route path="/publishers" element={<PublishersPage />} />
          <Route path="/publishers/:publisherId" element={<PublisherDetailPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="/admin" element={<Navigate to="/admin/datasources" replace />} />
          <Route path="/admin/datasources" element={<DataSourcesPage />} />
          <Route path="/admin/rules" element={<AlertingRulesPage />} />
          <Route path="/admin/slack" element={<SlackConfigPage />} />
          <Route path="/docs" element={<Navigate to="/docs/operativo" replace />} />
          <Route path="/docs/operativo" element={<OperationalDocsPage />} />
          <Route path="/docs/tecnico" element={<TechnicalDocsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AuthGuard>
  )
}
