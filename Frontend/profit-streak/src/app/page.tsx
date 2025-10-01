// src/app/page.tsx

import React from 'react';
import StockMarketQuery from '@/components/StockMarketQuery';

const Page = () => {
  return (
    <div className="main-container" style={{width: '100%', height: '100%'}}>
      <StockMarketQuery />
    </div>
  );
};

export default Page;
