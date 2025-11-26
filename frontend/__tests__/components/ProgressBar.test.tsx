import { render, screen } from '@testing-library/react'
import ProgressBar from '@/components/ProgressBar'

describe('ProgressBar', () => {
  it('renders without crashing', () => {
    render(<ProgressBar progress={50} />)
  })

  it('renders with correct progress width', () => {
    const { container } = render(<ProgressBar progress={50} />)
    const progressBar = container.querySelector('.bg-\\[\\#4169E1\\]')
    expect(progressBar).toHaveStyle({ width: '50%' })
  })

  it('clamps progress at 0%', () => {
    const { container } = render(<ProgressBar progress={-10} />)
    const progressBar = container.querySelector('.bg-\\[\\#4169E1\\]')
    expect(progressBar).toHaveStyle({ width: '0%' })
  })

  it('clamps progress at 100%', () => {
    const { container } = render(<ProgressBar progress={150} />)
    const progressBar = container.querySelector('.bg-\\[\\#4169E1\\]')
    expect(progressBar).toHaveStyle({ width: '100%' })
  })

  it('displays question count when provided', () => {
    render(<ProgressBar progress={50} questionCount={5} totalQuestions={10} />)
    expect(screen.getByText('5/10')).toBeInTheDocument()
  })

  it('does not display count when not provided', () => {
    render(<ProgressBar progress={50} />)
    expect(screen.queryByText(/\d+\/\d+/)).not.toBeInTheDocument()
  })

  it('applies correct styling classes', () => {
    const { container } = render(<ProgressBar progress={50} />)
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('fixed', 'top-0', 'left-0', 'right-0')
  })
})
