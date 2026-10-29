import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Remove rendered components between tests so one
// test's output cannot affect the next one.
afterEach(() => {
  cleanup()
})
