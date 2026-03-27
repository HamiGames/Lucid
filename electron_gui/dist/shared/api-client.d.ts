import { AxiosInstance, AxiosRequestConfig } from 'axios';
import { User, Session, SessionCreateRequest, SessionCreateResponse, Node, NodeRegistration, Block, Payout } from './types';
export declare function getServiceEndpoint(serviceName: string): string;
export declare class LucidAPIClient {
    protected client: AxiosInstance;
    private baseURL;
    private readonly torProxy;
    constructor(baseURL?: string);
    /**
     * Returns the underlying Axios instance for advanced use cases.
     * Prefer the helper HTTP methods whenever possible.
     */
    getHttpClient(): AxiosInstance;
    get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>;
    post<T = unknown, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig): Promise<T>;
    put<T = unknown, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig): Promise<T>;
    delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>;
    private getAuthToken;
    private handleAPIError;
    getUserProfile(userId: string): Promise<User>;
    updateUserProfile(userId: string, data: Partial<User>): Promise<User>;
    deleteUser(userId: string): Promise<void>;
    createSession(data: SessionCreateRequest): Promise<SessionCreateResponse>;
    getSession(sessionId: string): Promise<Session>;
    getUserSessions(userId: string): Promise<Session[]>;
    updateSession(sessionId: string, data: Partial<Session>): Promise<Session>;
    deleteSession(sessionId: string): Promise<void>;
    uploadChunk(sessionId: string, chunkData: FormData): Promise<void>;
    downloadChunk(chunkId: string): Promise<Blob>;
    getBlock(height: number): Promise<Block>;
    getLatestBlock(): Promise<Block>;
    getBlockchainInfo(): Promise<any>;
    registerNode(nodeData: NodeRegistration): Promise<Node>;
    getNode(nodeId: string): Promise<Node>;
    getNodeStatus(nodeId: string): Promise<any>;
    joinPool(nodeId: string, poolId: string): Promise<void>;
    leavePool(nodeId: string): Promise<void>;
    getPootScore(nodeId: string): Promise<number>;
    getPayoutHistory(nodeId: string): Promise<Payout[]>;
    getPayouts(): Promise<Payout[]>;
    login(email: string, signature: string): Promise<{
        token: string;
        user: User;
    }>;
    logout(): Promise<void>;
    verifyToken(token: string): Promise<User>;
    getSystemHealth(): Promise<any>;
    getAllUsers(): Promise<User[]>;
    getAllSessions(): Promise<Session[]>;
    getAllNodes(): Promise<Node[]>;
    verifySessionProof(sessionId: string): Promise<boolean>;
    getMerkleProof(chunkId: string): Promise<any>;
    getWalletBalance(address: string): Promise<{
        trx: number;
        usdt: number;
    }>;
    transferUSDT(fromAddress: string, toAddress: string, amount: number): Promise<string>;
}
