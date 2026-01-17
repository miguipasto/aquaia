function LoadingSpinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  }

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div
        className={`
          ${sizes[size]}
          border-4 border-gray-200 border-t-primary-500 rounded-full animate-spin
        `}
      />
    </div>
  )
}

export default LoadingSpinner
