import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ServerConnectionProvider } from './hooks/ServerConnectionContext'
import AppLayout from './components/layout/AppLayout'
import HomePage from './pages/HomePage'
import OnboardingPage from './pages/OnboardingPage'
import MissionChatPage from './pages/MissionChatPage'
import AgentProgressPage from './pages/AgentProgressPage'
import KnowledgeExplorerPage from './pages/KnowledgeExplorerPage'
import FieldChatPage from './pages/FieldChatPage'
import DiagnosisCardPage from './pages/DiagnosisCardPage'
import PackInfoPage from './pages/PackInfoPage'
import PackListPage from './pages/PackListPage'
import PipelineDebugPage from './pages/PipelineDebugPage'
import ObservationsPage from './pages/ObservationsPage'

export default function App() {
  return (
    <ServerConnectionProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/mission" element={<MissionChatPage />} />
          <Route path="/mission/progress" element={<AgentProgressPage />} />
          <Route path="/field" element={<FieldChatPage />} />
          <Route path="/field/diagnosis" element={<DiagnosisCardPage />} />
          <Route path="/packs" element={<PackListPage />} />
          <Route path="/packs/explorer" element={<KnowledgeExplorerPage />} />
          <Route path="/packs/:id" element={<PackInfoPage />} />
          <Route path="/observations" element={<ObservationsPage />} />
          <Route path="/debug" element={<PipelineDebugPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </ServerConnectionProvider>
  )
}
