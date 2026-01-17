import { AlertTriangle, XCircle, Info, CheckCircle } from 'lucide-react'

function Alert({ type = 'info', title, message, onClose }) {
  const configs = {
    error: {
      bgColor: 'bg-danger-50',
      borderColor: 'border-danger-200',
      textColor: 'text-danger-800',
      titleColor: 'text-danger-900',
      icon: XCircle,
      iconColor: 'text-danger-500',
    },
    warning: {
      bgColor: 'bg-warning-50',
      borderColor: 'border-warning-200',
      textColor: 'text-warning-800',
      titleColor: 'text-warning-900',
      icon: AlertTriangle,
      iconColor: 'text-warning-500',
    },
    success: {
      bgColor: 'bg-success-50',
      borderColor: 'border-success-200',
      textColor: 'text-success-800',
      titleColor: 'text-success-900',
      icon: CheckCircle,
      iconColor: 'text-success-500',
    },
    info: {
      bgColor: 'bg-primary-50',
      borderColor: 'border-primary-200',
      textColor: 'text-primary-800',
      titleColor: 'text-primary-900',
      icon: Info,
      iconColor: 'text-primary-500',
    },
  }

  const config = configs[type] || configs.info
  const Icon = config.icon

  return (
    <div className={`${config.bgColor} ${config.borderColor} border rounded-lg p-4`}>
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={config.iconColor} size={20} />
        </div>
        <div className="ml-3 flex-1">
          {title && (
            <h3 className={`text-sm font-medium ${config.titleColor}`}>
              {title}
            </h3>
          )}
          {message && (
            <div className={`text-sm ${config.textColor} ${title ? 'mt-1' : ''}`}>
              {message}
            </div>
          )}
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className={`ml-3 ${config.textColor} hover:opacity-75`}
          >
            <XCircle size={20} />
          </button>
        )}
      </div>
    </div>
  )
}

export default Alert
