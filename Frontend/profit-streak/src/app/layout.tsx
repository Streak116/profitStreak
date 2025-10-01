// src/app/layout.tsx

import React from 'react';
import './globals.css'; // You can add more global styles here
import './../styles/styles.css';

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Stock Market Insights</title>
      </head>
      <body>
        {children}
      </body>
    </html>
  );
};

export default Layout;
