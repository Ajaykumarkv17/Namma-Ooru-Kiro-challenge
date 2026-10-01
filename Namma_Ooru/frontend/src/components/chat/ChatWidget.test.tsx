import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ChatWidget } from './ChatWidget';

const { askChatMock } = vi.hoisted(() => ({ askChatMock: vi.fn() }));
vi.mock('../../api/client', () => ({ askChat: askChatMock }));

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ChatWidget />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.clearAllMocks());

describe('ChatWidget', () => {
  it('labels generated text and renders destination and external source links', async () => {
    askChatMock.mockResolvedValue({
      answer: 'A grounded answer.',
      unavailable: false,
      sources: [
        {
          destination_id: 'madurai-meenakshi-temple',
          name: 'Meenakshi Temple',
          url: 'https://example.gov.in/temple',
        },
      ],
    });
    const user = userEvent.setup();
    renderWidget();
    await user.type(screen.getByLabelText('Travel question'), 'Tell me about Meenakshi Temple');
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByText('AI-generated response')).toBeInTheDocument();
    expect(screen.getByText('A grounded answer.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Meenakshi Temple' })).toHaveAttribute(
      'href',
      '/destinations/madurai-meenakshi-temple',
    );
    expect(screen.getByRole('link', { name: 'Source link' })).toHaveAttribute(
      'href',
      'https://example.gov.in/temple',
    );
  });
});
