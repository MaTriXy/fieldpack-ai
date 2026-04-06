import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import HomePage from './pages/HomePage'
import MissionChatPage from './pages/MissionChatPage'
import AgentProgressPage from './pages/AgentProgressPage'
import KnowledgeExplorerPage from './pages/KnowledgeExplorerPage'
import FieldChatPage from './pages/FieldChatPage'
import DiagnosisCardPage from './pages/DiagnosisCardPage'
import PackInfoPage from './pages/PackInfoPage'
import PipelineDebugPage from './pages/PipelineDebugPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/mission" element={<MissionChatPage />} />
          <Route path="/mission/progress" element={<AgentProgressPage />} />
          <Route path="/field" element={<FieldChatPage />} />
          <Route path="/field/diagnosis" element={<DiagnosisCardPage />} />
          <Route path="/packs" element={<PackInfoPage />} />
          <Route path="/packs/explorer" element={<KnowledgeExplorerPage />} />
          <Route path="/debug" element={<PipelineDebugPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
