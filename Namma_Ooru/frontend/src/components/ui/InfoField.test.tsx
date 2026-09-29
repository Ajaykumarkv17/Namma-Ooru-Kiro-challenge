import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { INFORMATION_UNAVAILABLE, isUnavailable } from '../../lib/availability';
import { InfoField } from './InfoField';

describe('InfoField (Requirement 2.3)', () => {
  it('renders "Information unavailable" for a null value', () => {
    render(
      <dl>
        <InfoField label="Entry fee" value={null} />
      </dl>,
    );

    expect(screen.getByText('Entry fee')).toBeInTheDocument();
    expect(screen.getByText(INFORMATION_UNAVAILABLE)).toBeInTheDocument();
  });

  it('renders "Information unavailable" for an empty string', () => {
    render(
      <dl>
        <InfoField label="Address" value="   " />
      </dl>,
    );

    expect(screen.getByText(INFORMATION_UNAVAILABLE)).toBeInTheDocument();
  });

  it('renders a present value verbatim', () => {
    render(
      <dl>
        <InfoField label="Best time" value="November to February" />
      </dl>,
    );

    expect(screen.getByText('November to February')).toBeInTheDocument();
    expect(screen.queryByText(INFORMATION_UNAVAILABLE)).not.toBeInTheDocument();
  });

  it('uses the custom renderer only when a value exists', () => {
    render(
      <dl>
        <InfoField
          label="Website"
          render={(value) => <a href={value}>Visit</a>}
          value="https://example.org"
        />
      </dl>,
    );

    expect(screen.getByRole('link', { name: 'Visit' })).toHaveAttribute(
      'href',
      'https://example.org',
    );
  });

  it('does not invoke the renderer for a null value', () => {
    render(
      <dl>
        <InfoField
          label="Website"
          render={() => <a href="/should-not-render">Visit</a>}
          value={null}
        />
      </dl>,
    );

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText(INFORMATION_UNAVAILABLE)).toBeInTheDocument();
  });

  it('classifies availability of values', () => {
    expect(isUnavailable(null)).toBe(true);
    expect(isUnavailable(undefined)).toBe(true);
    expect(isUnavailable('')).toBe(true);
    expect(isUnavailable('  ')).toBe(true);
    expect(isUnavailable('open')).toBe(false);
    expect(isUnavailable(0)).toBe(false);
    expect(isUnavailable(90)).toBe(false);
  });
});
