import { Route, Routes } from 'react-router-dom'
import { Layout } from './layout/Layout'
import { AppProvider } from './state/AppContext'
import { Dashboard } from './pages/Dashboard'
import { Documents } from './pages/Documents'
import { DocumentDetail } from './pages/DocumentDetail'
import { Ingestion } from './pages/Ingestion'
import { Connectors } from './pages/Connectors'
import { Classification } from './pages/Classification'
import { Ontology } from './pages/Ontology'
import { Search } from './pages/Search'
import { RagPage } from './pages/RagPage'
import { ReviewQueue } from './pages/ReviewQueue'
import { ScaleSimulator } from './pages/ScaleSimulator'
import { SystemHealth } from './pages/SystemHealth'

export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/documents/:id" element={<DocumentDetail />} />
          <Route path="/ingestion" element={<Ingestion />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/classification" element={<Classification />} />
          <Route path="/ontology" element={<Ontology />} />
          <Route path="/search" element={<Search />} />
          <Route path="/rag" element={<RagPage />} />
          <Route path="/reviews" element={<ReviewQueue />} />
          <Route path="/scale-simulator" element={<ScaleSimulator />} />
          <Route path="/system-health" element={<SystemHealth />} />
        </Route>
      </Routes>
    </AppProvider>
  )
}
