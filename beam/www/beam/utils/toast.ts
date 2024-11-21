import { type ToastProps, useToast } from 'vue-toast-notification'
import 'vue-toast-notification/dist/theme-default.css'

const useBeamToast = (props?: ToastProps) => {
	return useToast({
		position: 'top',
		dismissible: true,
		duration: 3000,
		queue: false,
		...props,
	})
}

export { useBeamToast }
