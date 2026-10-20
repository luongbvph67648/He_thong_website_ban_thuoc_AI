import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { RouterProvider } from 'react-router-dom'
import './lib/dayjs'
import { router } from './router'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <ConfigProvider locale={viVN} theme={{ token: { colorPrimary: '#1677ff', colorLink: '#1677ff', colorText: '#243b53', colorTextSecondary: '#6b7a90', colorBorder: '#e2e7ee', colorBgContainer: '#ffffff' } }}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  )
}
