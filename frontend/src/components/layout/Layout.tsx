import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import ChatWidget from '@/components/chat/ChatWidget'
import ToastContainer from './ToastContainer'

export default function Layout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Outlet />
      </div>
      <ChatWidget />
      <ToastContainer />
    </div>
  )
}
