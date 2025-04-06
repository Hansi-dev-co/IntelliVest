import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button'; // Shadcn components are correctly set up
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { File } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

// API endpoint
const API_BASE_URL = "/intellivest-back-end.py";

// Helper function to fetch data from the backend
const fetchData = async (endpoint, method = 'GET', body = null) => {
    try 
    {
        const headers = 
        {
            'Content-Type': 'application/json',
        };

        const config = 
        {
            method,
            headers,
        };

        if (body) 
            {
            config.body = JSON.stringify(body);
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        if (!response.ok) 
        {
            throw new Error(`HTTP Error! Status: ${response.status}`);
        }
        return await response.json();
    } 
    catch (error) 
    {
        console.error('Error Fetching Data: ', error);
        throw error; // Re-throw to be caught by the component
    }
};

const FinancialAssistant = () => {
    const [ticker, setTicker] = useState('');
    const [summary, setSummary] = useState('');
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState('');
    const [portfolioFile, setPortfolioFile] = useState(null);
    const [portfolioAnalysis, setPortfolioAnalysis] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const getSummary = useCallback(async () => {
        if (!ticker) 
        {
            setError('Please enter a stock ticker 📊');
            return;
        }
        setLoading(true);
        setError(null);
        setSummary('');
        try 
        {
            const data = await fetchData(`/summary/${ticker}`);
            setSummary(data.summary);
        } 
        catch (err) 
        {
            setError(err.message || 'Failed to fetch summary');
        } 
        finally 
        {
            setLoading(false);
        }
    }, [ticker]);

    const askQuestion = useCallback(async () => {
        if (!question) 
        {
            setError('Please enter a question');
            return;
        }
        setLoading(true);
        setError(null);
        setAnswer('');
        try 
        {
            const data = await fetchData('/question', 'POST', { question });
            setAnswer(data.answer);
        } 
        catch (err) 
        {
            setError(err.message || 'Failed to get answer');
        }
        finally 
        {
            setLoading(false);
        }
    }, [question]);

    const handlePortfolioUpload = useCallback(async () => {
        if (!portfolioFile) {
            setError('Please upload a portfolio file');
            return;
        }
        setLoading(true);
        setError(null);
        setPortfolioAnalysis('');

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const text = e.target?.result;
                if (typeof text === 'string') {
                    const data = await fetchData('/portfolio/analyze', 'POST', { csvData: text });
                    setPortfolioAnalysis(data.analysis);
                } else {
                    setError("Error reading file");
                }
            } catch (err) {
                setError(err.message || 'Failed to analyze portfolio');
            } finally {
                setLoading(false);
            }
        };
        reader.onerror = () => {
            setError('Failed to read the file.');
            setLoading(false);
        }
        reader.readAsText(portfolioFile);
    }, [portfolioFile]);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setPortfolioFile(e.target.files[0]);
        }
    };

    return (
        <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-4 md:p-8">
            <div className="max-w-4xl mx-auto space-y-6">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white text-center">
                    GenAI Financial Assistant
                </h1>

                {error && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {/* Stock Summary Section */}
                <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-4 md:p-6 space-y-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Stock Summary</h2>
                    <div className="flex flex-col sm:flex-row gap-4">
                        <Input
                            type="text"
                            placeholder="Enter stock ticker (e.g., AAPL)"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value)}
                            className="w-full sm:w-auto"
                            disabled={loading}
                        />
                        <Button onClick={getSummary} disabled={loading} className="w-full sm:w-auto">
                            {loading ? 'Loading...' : 'Get Summary'}
                        </Button>
                    </div>
                    {summary && (
                        <Textarea
                            value={summary}
                            readOnly
                            className="bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white"
                            rows={4}
                        />
                    )}
                </div>

                {/* Educational Q&A Section */}
                <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-4 md:p-6 space-y-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Financial Q&A</h2>
                    <div className="flex flex-col sm:flex-row gap-4">
                        <Input
                            type="text"
                            placeholder="Ask a financial question"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            className="w-full sm:w-auto"
                            disabled={loading}
                        />
                        <Button onClick={askQuestion} disabled={loading} className="w-full sm:w-auto">
                            {loading ? 'Loading...' : 'Get Answer'}
                        </Button>
                    </div>
                    {answer && (
                        <Textarea
                            value={answer}
                            readOnly
                            className="bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white"
                            rows={4}
                        />
                    )}
                </div>

                {/* Portfolio Analysis Section */}
                <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-4 md:p-6 space-y-4">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Portfolio Analysis</h2>
                    <div className="flex flex-col sm:flex-row gap-4 items-center">
                        <Input
                            type="file"
                            onChange={handleFileChange}
                            className="w-full sm:w-auto"
                            accept=".csv"
                            id="portfolio-upload"
                            disabled={loading}
                        />
                        <label htmlFor="portfolio-upload" className="sr-only">Upload Portfolio CSV</label>
                        <Button onClick={handlePortfolioUpload} disabled={loading} className="w-full sm:w-auto">
                            {loading ? 'Loading...' : 'Analyze Portfolio'}
                        </Button>
                    </div>
                    {portfolioAnalysis && (
                        <Textarea
                            value={portfolioAnalysis}
                            readOnly
                            className="bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white"
                            rows={4}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default FinancialAssistant;