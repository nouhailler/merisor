export interface Customer {
  id: number;
  name: string;
  email: string;
}

export interface Order {
  id: number;
  customerId: number;
  description: string;
  amount: number;
  createdAt: Date;
}

