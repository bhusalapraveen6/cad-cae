import { useStore } from '@/store'

export default function ToastContainer() {
  const { toasts, removeToast } = useStore()
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`} onClick={() => removeToast(t.id)}>
          <span>
            {t.type === 'success' ? '✓' : t.type === 'error' ? '✗' : 'ℹ'}
          </span>
          {t.message}
        </div>
      ))}
    </div>
  )
}
